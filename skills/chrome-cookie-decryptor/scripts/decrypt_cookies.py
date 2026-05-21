"""
Chrome v20 Cookie Decryptor
Decrypts Chrome ABE-encrypted cookies from local SQLite database.

Requirements: admin privileges, PythonForWindows, pycryptodome, pywin32
Usage: python decrypt_cookies.py [--domain DOMAIN] [--output OUTPUT] [--chrome-profile PROFILE]
"""
import argparse
import base64
import io
import json
import os
import shutil
import sqlite3
import struct
import sys
import tempfile
import pathlib
from contextlib import contextmanager

try:
    import ctypes
    import ctypes.wintypes
    import windows
    import windows.crypto
    import windows.generated_def as gdef
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install PythonForWindows pycryptodome cryptography pywin32")
    sys.exit(1)


# ============================================================
# SYSTEM impersonation
# ============================================================

@contextmanager
def impersonate_lsass():
    """Impersonate lsass.exe to get SYSTEM privilege for DPAPI decryption.

    Chrome's app_bound_encrypted_key is encrypted with SYSTEM DPAPI.
    Normal admin users can't decrypt it — we need to borrow lsass.exe's
    SYSTEM token via SeDebugPrivilege.
    """
    original_token = windows.current_thread.token
    try:
        windows.current_process.token.enable_privilege("SeDebugPrivilege")
        proc = next(p for p in windows.system.processes if p.name == "lsass.exe")
        lsass_token = proc.token
        impersonation_token = lsass_token.duplicate(
            type=gdef.TokenImpersonation,
            impersonation_level=gdef.SecurityImpersonation
        )
        windows.current_thread.token = impersonation_token
        yield
    finally:
        windows.current_thread.token = original_token


# ============================================================
# Key blob parsing
# ============================================================

def parse_key_blob(blob_data):
    """Parse the double-DPAPI decrypted key blob.

    Format: [header_len:4][header][content_len:4][flag:1][crypto data...]
    flag 0x01 = AES-256-GCM (Chrome <133)
    flag 0x02 = ChaCha20-Poly1305 (Chrome 133-136)
    flag 0x03 = AES-256-GCM + CNG KSP (Chrome 137+)
    """
    buffer = io.BytesIO(blob_data)
    parsed = {}

    header_len = struct.unpack('<I', buffer.read(4))[0]
    parsed['header'] = buffer.read(header_len)
    content_len = struct.unpack('<I', buffer.read(4))[0]

    if header_len + content_len + 8 != len(blob_data):
        raise ValueError(
            f"Blob size mismatch: header_len={header_len}, content_len={content_len}, "
            f"total={len(blob_data)}, expected={header_len + content_len + 8}"
        )

    parsed['flag'] = buffer.read(1)[0]

    if parsed['flag'] in (1, 2):
        parsed['iv'] = buffer.read(12)
        parsed['ciphertext'] = buffer.read(32)
        parsed['tag'] = buffer.read(16)
    elif parsed['flag'] == 3:
        parsed['encrypted_aes_key'] = buffer.read(32)
        parsed['iv'] = buffer.read(12)
        parsed['ciphertext'] = buffer.read(32)
        parsed['tag'] = buffer.read(16)
    else:
        raise ValueError(
            f"Unsupported Chrome encryption flag: 0x{parsed['flag']:02x}. "
            f"This Chrome version may use a newer encryption scheme."
        )

    return parsed


# ============================================================
# CNG decryption
# ============================================================

def decrypt_with_cng(input_data):
    """Decrypt data using Windows CNG Key Storage Provider.

    Chrome 137+ stores the AES key in the Microsoft Software KSP
    under the name "Google Chromekey1" (machine-level key).
    """
    ncrypt = ctypes.windll.NCRYPT

    hProvider = gdef.NCRYPT_PROV_HANDLE()
    status = ncrypt.NCryptOpenStorageProvider(
        ctypes.byref(hProvider), "Microsoft Software Key Storage Provider", 0
    )
    if status != 0:
        raise RuntimeError(
            f"NCryptOpenStorageProvider failed: 0x{status & 0xFFFFFFFF:08x}. "
            f"Is this Windows 10+?"
        )

    hKey = gdef.NCRYPT_KEY_HANDLE()
    status = ncrypt.NCryptOpenKey(
        hProvider, ctypes.byref(hKey), "Google Chromekey1", 0, 0x40  # NCRYPT_MACHINE_KEY_FLAG
    )
    if status != 0:
        ncrypt.NCryptFreeObject(hProvider)
        raise RuntimeError(
            f"NCryptOpenKey('Google Chromekey1') failed: 0x{status & 0xFFFFFFFF:08x}. "
            f"Possible causes: Chrome not installed via standard installer, "
            f"or Chrome version < 127, or not running as admin."
        )

    pcbResult = gdef.DWORD(0)
    input_buffer = (ctypes.c_ubyte * len(input_data)).from_buffer_copy(input_data)

    # First call: get output size
    status = ncrypt.NCryptDecrypt(
        hKey, input_buffer, len(input_buffer), None, None, 0, ctypes.byref(pcbResult), 0x40
    )
    if status != 0:
        ncrypt.NCryptFreeObject(hKey)
        ncrypt.NCryptFreeObject(hProvider)
        raise RuntimeError(f"NCryptDecrypt (size query) failed: 0x{status & 0xFFFFFFFF:08x}")

    # Second call: actual decrypt
    output_buffer = (ctypes.c_ubyte * pcbResult.value)()
    status = ncrypt.NCryptDecrypt(
        hKey, input_buffer, len(input_buffer), None,
        output_buffer, pcbResult.value, ctypes.byref(pcbResult), 0x40
    )
    if status != 0:
        ncrypt.NCryptFreeObject(hKey)
        ncrypt.NCryptFreeObject(hProvider)
        raise RuntimeError(f"NCryptDecrypt failed: 0x{status & 0xFFFFFFFF:08x}")

    result = bytes(output_buffer[:pcbResult.value])
    ncrypt.NCryptFreeObject(hKey)
    ncrypt.NCryptFreeObject(hProvider)
    return result


# ============================================================
# Master key derivation
# ============================================================

def byte_xor(ba1, ba2):
    return bytes([a ^ b for a, b in zip(ba1, ba2)])


def derive_v20_master_key(parsed):
    """Derive the AES master key from parsed key blob.

    Each Chrome version range uses a different decryption strategy:
    - flag=0x01: AES-256-GCM with hardcoded key (Chrome <133)
    - flag=0x02: ChaCha20-Poly1305 with hardcoded key (Chrome 133-136)
    - flag=0x03: CNG KSP decrypt + XOR (Chrome 137+)
    """
    if parsed['flag'] == 1:
        aes_key = bytes.fromhex(
            "B31C6E241AC846728DA9C1FAC4936651CFFB944D143AB816276BCC6DA0284787"
        )
        cipher = AESGCM(aes_key)

    elif parsed['flag'] == 2:
        chacha20_key = bytes.fromhex(
            "E98F37D7F4E1FA433D19304DC2258042090E2D1D7EEA7670D41F738D08729660"
        )
        cipher = ChaCha20Poly1305(chacha20_key)

    elif parsed['flag'] == 3:
        xor_key = bytes.fromhex(
            "CCF8A1CEC56605B8517552BA1A2D061C03A29E90274FB2FCF59BA4B75C392390"
        )
        with impersonate_lsass():
            decrypted_aes_key = decrypt_with_cng(parsed['encrypted_aes_key'])
        xored_aes_key = byte_xor(decrypted_aes_key, xor_key)
        cipher = AESGCM(xored_aes_key)

    return cipher.decrypt(parsed['iv'], parsed['ciphertext'] + parsed['tag'], None)


# ============================================================
# Cookie decryption
# ============================================================

def decrypt_cookies(master_key, cookie_db_path, domain=None):
    """Decrypt cookies from the database using the master key.

    Handles both v20 (AES-GCM) and v10 (DPAPI) encrypted cookies.
    v20 cookies have a 32-byte integrity hash prefix that is stripped.
    """
    tmp_dir = tempfile.mkdtemp()
    tmp_db = os.path.join(tmp_dir, "Cookies")
    shutil.copy2(cookie_db_path, tmp_db)

    con = sqlite3.connect(pathlib.Path(tmp_db).as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()

    if domain:
        cur.execute(
            "SELECT host_key, name, CAST(encrypted_value AS BLOB) FROM cookies WHERE host_key LIKE ?",
            (f"%{domain}%",)
        )
    else:
        cur.execute("SELECT host_key, name, CAST(encrypted_value AS BLOB) FROM cookies")

    rows = cur.fetchall()
    con.close()
    shutil.rmtree(tmp_dir)

    cipher = AESGCM(master_key)
    results = []

    for host, name, enc_val in rows:
        if not enc_val or len(enc_val) < 3:
            continue

        prefix = enc_val[:3]

        if prefix == b"v20":
            try:
                iv = enc_val[3:15]
                ct = enc_val[15:-16]
                tag = enc_val[-16:]
                dec = cipher.decrypt(iv, ct + tag, None)
                # First 32 bytes are domain integrity hash, skip them
                value = dec[32:].decode("utf-8")
                results.append({"name": name, "value": value, "domain": host})
            except Exception:
                pass  # Skip cookies that fail to decrypt

        elif prefix == b"v10":
            try:
                import win32crypt
                _, data = win32crypt.CryptUnprotectData(enc_val[3:], None, None, None, 0)
                results.append({"name": name, "value": data.decode("utf-8"), "domain": host})
            except Exception:
                pass

    return results


# ============================================================
# Pre-flight checks
# ============================================================

def check_chrome_running():
    """Check if Chrome is currently running."""
    try:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
            capture_output=True, text=True, timeout=5
        )
        return "chrome.exe" in result.stdout.lower()
    except Exception:
        return False


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Decrypt Chrome v20 ABE-encrypted cookies from local database"
    )
    parser.add_argument("--domain", help="Filter by domain (e.g. bilibili.com, github.com)")
    parser.add_argument("--output", help="Output JSON file path (default: temp dir)")
    parser.add_argument("--chrome-profile", default="Default",
                        help="Chrome profile directory name (default: Default)")
    args = parser.parse_args()

    # Pre-flight
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("Error: This script requires administrator privileges.")
        print("Right-click your terminal and select 'Run as administrator'.")
        sys.exit(1)

    if check_chrome_running():
        print("Error: Chrome is still running. Please close Chrome first.")
        print("  The cookie database is locked while Chrome is open.")
        sys.exit(1)

    local_state = os.path.join(
        os.environ["LOCALAPPDATA"],
        r"Google\Chrome\User Data\Local State"
    )
    cookie_db = os.path.join(
        os.environ["LOCALAPPDATA"],
        rf"Google\Chrome\User Data\{args.chrome_profile}\Network\Cookies"
    )

    if not os.path.exists(local_state):
        print(f"Error: Local State not found: {local_state}")
        print("  Is Chrome installed?")
        sys.exit(1)
    if not os.path.exists(cookie_db):
        print(f"Error: Cookie DB not found: {cookie_db}")
        print(f"  Check --chrome-profile (current: '{args.chrome_profile}')")
        sys.exit(1)

    # Step 1: Read encrypted key
    with open(local_state, "r", encoding="utf-8") as f:
        state = json.load(f)

    if "app_bound_encrypted_key" not in state.get("os_crypt", {}):
        print("Error: No app_bound_encrypted_key found in Local State.")
        print("  This Chrome version may not use ABE encryption.")
        sys.exit(1)

    key_b64 = state["os_crypt"]["app_bound_encrypted_key"]
    key_blob_encrypted = base64.b64decode(key_b64)[4:]  # Remove APPB prefix

    # Step 2: SYSTEM DPAPI decrypt
    print("[1/4] SYSTEM DPAPI decrypt...")
    try:
        with impersonate_lsass():
            key_blob_system = windows.crypto.dpapi.unprotect(key_blob_encrypted)
    except Exception as e:
        print(f"Error: SYSTEM DPAPI decryption failed: {e}")
        print("  Are you running as administrator?")
        sys.exit(1)

    # Step 3: User DPAPI decrypt
    print("[2/4] User DPAPI decrypt...")
    try:
        key_blob_user = windows.crypto.dpapi.unprotect(key_blob_system)
    except Exception as e:
        print(f"Error: User DPAPI decryption failed: {e}")
        sys.exit(1)

    # Step 4: Parse and derive master key
    print("[3/4] Derive master key (CNG + XOR)...")
    try:
        parsed = parse_key_blob(key_blob_user)
        master_key = derive_v20_master_key(parsed)
    except Exception as e:
        print(f"Error: Master key derivation failed: {e}")
        sys.exit(1)

    # Step 5: Decrypt cookies
    print("[4/4] Decrypt cookies...")
    results = decrypt_cookies(master_key, cookie_db, domain=args.domain)

    # Output
    output_path = args.output or os.path.join(tempfile.gettempdir(), "chrome_cookies.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDecrypted {len(results)} cookies")
    print(f"Saved to: {output_path}")

    for c in results:
        print(f"  {c['name']} ({c['domain']}): {c['value'][:60]}")


if __name__ == "__main__":
    main()
