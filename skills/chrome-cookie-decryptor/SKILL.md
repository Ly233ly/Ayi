---
name: chrome-cookie-decryptor
description: 从本地 Chrome 浏览器提取并解密 Cookie（支持 Chrome v20 ABE 加密）。当用户提到"提取 Cookie"、"Chrome Cookie"、"本地 Cookie"、"拿登录态"、"Cookie 解密"、"获取浏览器 Cookie"、"B站 Cookie"、"微博 Cookie"、"登录凭证"、"复用浏览器登录状态"、"爬虫登录"、"自动化登录"、"cookie 注入"、"playwright cookie"、"selenium cookie" 时必须触发。即使用户没有明确说"解密"，只要涉及从本地 Chrome 获取登录态用于自动化，都应主动调用此技能。
---

# Chrome Cookie Decryptor

从本地 Chrome 浏览器提取解密后的 Cookie，输出 JSON 格式，可直接用于 Playwright / Selenium / requests 注入。

## 前置条件

- **管理员权限** — 脚本需要 SeDebugPrivilege 来 impersonate lsass
- **Chrome 已关闭** — Chrome 运行时独占锁 Cookie 文件，无法读取
- **Python 依赖** — `pip install PythonForWindows pycryptodome cryptography pywin32`

## 使用方式

```bash
# 提取指定域名的 Cookie
python <skill-dir>/scripts/decrypt_cookies.py --domain bilibili.com

# 提取所有域名的 Cookie
python <skill-dir>/scripts/decrypt_cookies.py

# 指定输出文件路径
python <skill-dir>/scripts/decrypt_cookies.py --domain bilibili.com --output cookies.json

# 指定 Chrome Profile（多账户场景）
python <skill-dir>/scripts/decrypt_cookies.py --domain bilibili.com --chrome-profile "Profile 1"
```

## 输出格式

```json
[
  {"name": "SESSDATA", "value": "...", "domain": ".bilibili.com"},
  {"name": "bili_jct", "value": "...", "domain": ".bilibili.com"}
]
```

## Playwright 注入示例

```python
import json, asyncio
from playwright.async_api import async_playwright

async def inject_cookies(cookies_file, target_url):
    with open(cookies_file) as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        await context.add_cookies([
            {"name": c["name"], "value": c["value"],
             "domain": c["domain"], "path": "/"}
            for c in cookies
        ])
        page = await context.new_page()
        await page.goto(target_url)
        # 此时已是登录状态
        return page
```

## 常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `Chrome is still running` | Chrome 进程未关闭 | 关闭 Chrome，检查任务管理器 |
| `Missing dependencies` | 缺少 Python 包 | `pip install PythonForWindows pycryptodome cryptography pywin32` |
| `NCryptOpenKey failed` | CNG key 找不到 | 确认 Chrome 版本 >= 127，且以管理员运行 |
| `PermissionError` | 没有管理员权限 | 右键"以管理员身份运行"终端 |
| `Cookie DB not found` | Profile 路径错误 | 检查 `--chrome-profile` 参数 |

## 技术原理

Chrome v20 使用 5 层嵌套加密：SYSTEM DPAPI → 用户 DPAPI → CNG KSP → XOR → AES-GCM。脚本自动完成全部解密链路。

详细技术文档见 `references/technical_details.md`，包含：
- 完整加密架构图
- 每一步的原理和代码
- CNG key 名称和 XOR key 的定位过程
- 132 字节 blob 逐字节解析
- 20+ 种失败尝试记录
- 安全启示分析
