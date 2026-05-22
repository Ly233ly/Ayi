# 即梦提示词爬取工具 v2.0

从即梦网站（jimeng.jianying.com）批量爬取用户生成图片的提示词。

## 快速开始

### 1. 启动 Chrome（4 个端口并行）

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9230 --user-data-dir=/tmp/chrome-9230 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9231 --user-data-dir=/tmp/chrome-9231 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9232 --user-data-dir=/tmp/chrome-9232 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9233 --user-data-dir=/tmp/chrome-9233 &
```

### 2. 安装依赖

```bash
npm install
```

### 3. 运行爬取

```bash
# 单实例
node jimeng-scraper.js --port 9230 --output batch1.json --max 500

# 4 端口并行（推荐）
node jimeng-scraper.js --port 9230 --output batch1.json --max 500 &
node jimeng-scraper.js --port 9231 --output batch2.json --max 500 &
node jimeng-scraper.js --port 9232 --output batch3.json --max 500 &
node jimeng-scraper.js --port 9233 --output batch4.json --max 500 &
```

### 4. 合并数据

```bash
node -e "
const fs = require('fs');
const all = [];
const seen = new Set();
for (let i = 1; i <= 4; i++) {
  try {
    const data = JSON.parse(fs.readFileSync('batch'+i+'.json','utf-8'));
    data.forEach(d => {
      if (!seen.has(d.url)) { seen.add(d.url); all.push(d); }
    });
  } catch {}
}
fs.writeFileSync('jimeng-all.json', JSON.stringify(all, null, 2));
console.log('Total unique items:', all.length);
"
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 9223 | Chrome 远程调试端口 |
| `--output` | jimeng-prompts.json | 输出文件名 |
| `--max` | 100 | 最大爬取条数 |

## 数据格式

```json
{
  "prompt": "提示词文本...",
  "model": "4.5",
  "ratio": "9:16",
  "author": "作者名",
  "date": "2026-03-01",
  "url": "https://jimeng.jianying.com/ai-tool/work-detail/...",
  "scrapedAt": "2026-05-22T10:00:00.000Z"
}
```

## v2.0 特性

- **智能弹窗检测**：自动识别详情页跳转并返回首页
- **多选择器备选**：6 个图片选择器，自动切换
- **健康监控**：每 30 秒打印进度、速度、错误数
- **自动恢复**：连续错误或卡住时自动刷新页面
- **优雅退出**：Ctrl+C 安全退出，已采集数据不丢失
- **追加写入**：每条数据即时写入，中断不丢失
- **速度显示**：实时显示采集速度（条/分钟）

## 注意事项

- 爬取过程中不要手动操作 Chrome 窗口
- Ctrl+C 安全退出，数据不会丢失
- 如果某个 Chrome 崩溃了，关掉提示窗口，重新启动该端口
- 详见 `jimeng-scraper-guide.md`
