# 即梦爬取运行手册

> 把这个文件给 AI，AI 就知道该做什么、怎么做。

## 项目是什么

从即梦网站（jimeng.jianying.com）批量爬取用户生成图片的提示词，用于优化 AI 图像生成提示词技能。

- **脚本**：`jimeng-scraper.js`（v2.0，已修复详情页跳转、页面错误恢复、健康监控等 bug）
- **当前数据**：1764 条去重（目标 2000 条，还差 236 条）
- **数据文件**：`jimeng-all.json`（去重后的完整数据）

## 你要做什么

### 第一步：启动 4 个 Chrome 实例

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9230 --user-data-dir=/tmp/chrome-9230 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9231 --user-data-dir=/tmp/chrome-9231 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9232 --user-data-dir=/tmp/chrome-9232 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9233 --user-data-dir=/tmp/chrome-9233 &
```

验证：
```bash
sleep 3 && netstat -ano | grep -E "9230|9231|9232|9233" | grep LISTENING
```

### 第二步：运行爬取（4 端口并行）

```bash
cd /c/Users/Administrator/Desktop/daliy/jimeng-scraper
node jimeng-scraper.js --port 9230 --output batch1.json --max 500 &
node jimeng-scraper.js --port 9231 --output batch2.json --max 500 &
node jimeng-scraper.js --port 9232 --output batch3.json --max 500 &
node jimeng-scraper.js --port 9233 --output batch4.json --max 500 &
```

### 第三步：检查进度

```bash
for f in batch*.json; do echo "$f: $(grep -c '"prompt"' "$f" 2>/dev/null || echo 0) items"; done
```

### 第四步：合并数据

```bash
node -e "
const fs = require('fs');
const all = [];
const seen = new Set();
// 加载已有数据
try {
  const existing = JSON.parse(fs.readFileSync('jimeng-all.json','utf-8'));
  existing.forEach(d => { seen.add(d.url); all.push(d); });
  console.log('已有:', existing.length);
} catch {}
// 合并 batch 文件
for (let i = 1; i <= 4; i++) {
  try {
    const data = JSON.parse(fs.readFileSync('batch'+i+'.json','utf-8'));
    let added = 0;
    data.forEach(d => {
      if (!seen.has(d.url)) { seen.add(d.url); all.push(d); added++; }
    });
    console.log('batch'+i+':', data.length, '条,', added, '条新增');
  } catch {}
}
fs.writeFileSync('jimeng-all.json', JSON.stringify(all, null, 2));
console.log('总计去重:', all.length, '条');
"
```

### 第五步：查看当前数据量

```bash
node -e "console.log(JSON.parse(require('fs').readFileSync('jimeng-all.json','utf-8')).length, '条')"
```

## 关键参数

| 参数 | 说明 | 当前值 |
|------|------|--------|
| `--port` | Chrome 端口 | 9230-9233 |
| `--output` | 输出文件 | batch1-4.json |
| `--max` | 每端口最大条数 | 500 |

## 脚本行为

- 每条数据**即时写入文件**，中断不丢失
- 每 50 条暂停 5-10 秒（防反爬）
- 每 30 秒打印健康检查（进度、速度、错误数）
- 连续 3 次错误自动刷新页面
- 连续 5 轮无新数据自动刷新
- 最大刷新 20 次后退出
- Ctrl+C 安全退出

## 输出日志示例

```
📌 使用选择器: .cover-UJwtaY
页面 15 张图片, 已采集 0 条
[1/500] 5.8条/分 Model:3.1 长度:57
[2/500] 6.4条/分 Model:4.1 长度:173
--- 批次暂停 5s ---
📊 健康检查: 50/500 条, 速度 6.0 条/分, 刷新 0 次, 错误 0
```

## 常见问题

| 问题 | 解决 |
|------|------|
| 无法连接 Chrome | 确认 Chrome 已启动并带 `--remote-debugging-port` |
| 采集速度慢 | 正常，约 5-6 条/分钟，4 端口并行约 20-24 条/分 |
| 页面错误/卡住 | 脚本会自动刷新恢复，看日志 |
| Chrome 崩溃 | 关掉崩溃提示，重新启动该端口 |
| VPN 问题 | 开启 VPN（端口 7890，FlClash） |

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

## 数据分析（1764 条）

### 模型分布
| 模型 | 占比 |
|------|------|
| 3.1 | 22.3% |
| 4.5 | 19.6% |
| 4.0 | 19.2% |
| 4.1 | 13.8% |
| 3.0 | 8.7% |
| 5.0 Lite | 7.9% |
| 4.6/4.7 | 8.4% |

### 高频词 TOP 10
细腻(423)、梦幻(301)、写实(294)、精致(277)、氛围感(264)、超高清(228)、高级感(196)、极繁主义(193)、视觉冲击(177)、超清(169)

### 提示词特征
- 平均长度：202 字符
- 语言：100% 中文，63.2% 混合英文
- 主流比例：9:16 (70.9%)

## 文件结构

```
jimeng-scraper/
├── RUNBOOK.md              ← 本文件（给 AI 看的）
├── README.md               ← 使用说明
├── jimeng-scraper.js       ← 核心脚本 v2.0
├── jimeng-scraper-guide.md ← 详细文档
├── package.json            ← 依赖
├── jimeng-all.json         ← 去重数据（运行后生成）
├── batch1.json             ← 端口 9230 数据（运行后生成）
├── batch2.json             ← 端口 9231 数据
├── batch3.json             ← 端口 9232 数据
└── batch4.json             ← 端口 9233 数据
```
