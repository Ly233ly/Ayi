# 即梦提示词爬取指南

> 最后更新：2026-05-22
> 当前进度：1764 条去重数据（目标 2000 条，还需 236 条）
> 脚本版本：v2.0（已修复详情页跳转、页面错误恢复、健康监控）
> 独立目录：`C:\Users\Administrator\Desktop\daliy\jimeng-scraper\`

## 项目概述

从即梦网站（jimeng.jianying.com）批量爬取用户生成图片的提示词，用于优化 `ai-image-prompt` skill。

## 文件结构

```
jimeng-scraper/                ← 独立目录（可直接复制使用）
├── RUNBOOK.md                 ← AI运行手册（给AI看的）
├── README.md                  ← 使用说明（给人看的）
├── jimeng-scraper.js          ← 核心脚本 v2.0
├── jimeng-scraper-guide.md    ← 本指南（详细文档）
├── package.json               ← 依赖
└── package-lock.json

scripts/                       ← 原始目录（保留兼容）
├── jimeng-scraper.js          ← 同步副本
├── jimeng-scraper-guide.md    ← 同步副本
├── jimeng-all.json            ← 去重数据（1764条）
├── batch1-4.json              ← 各端口爬取结果
└── package.json
```

## 环境要求

- Windows 11
- Chrome 浏览器（已安装在 `C:\Program Files\Google\Chrome\Application\chrome.exe`）
- Node.js（已安装）
- Playwright（已安装，通过 npm）

## 快速启动步骤

### 第一步：启动 4 个 Chrome 实例

打开 Git Bash 或终端，运行：

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9230 --user-data-dir=/tmp/chrome-scraper-9230 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9231 --user-data-dir=/tmp/chrome-scraper-9231 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9232 --user-data-dir=/tmp/chrome-scraper-9232 &
"/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9233 --user-data-dir=/tmp/chrome-scraper-9233 &
```

验证端口是否启动：
```bash
sleep 3 && netstat -ano | findstr "9230\|9231\|9232\|9233" | findstr LISTENING
```

应该看到 4 个端口都在 LISTENING。

### 第二步：告诉 Claude 启动爬取

对 Claude 说：
```
读取 C:\Users\Administrator\Desktop\daliy\scripts\jimeng-scraper-guide.md，然后继续爬取即梦提示词，目标 2000 条。当前已有 366 条在 jimeng-all.json 中。
```

Claude 会：
1. 读取本指南文件
2. 启动 4 个并行 agent，每个连接一个 Chrome 端口
3. 每个 agent 运行 `jimeng-scraper.js` 脚本
4. 脚本会自动滚动页面、点击图片、提取提示词、保存到 batch 文件

### 第三步：监控进度

Claude 会定期检查进度：
```bash
for f in batch*.json; do echo "$f: $(grep -c '"prompt"' "$f" 2>/dev/null || echo 0) items"; done
```

### 第四步：合并数据

爬取完成后，Claude 会运行合并脚本：
```bash
node -e "
const fs = require('fs');
const all = [];
const seen = new Set();
for (let i = 1; i <= 4; i++) {
  try {
    const data = JSON.parse(fs.readFileSync('batch'+i+'.json','utf-8'));
    data.forEach(d => {
      if (!seen.has(d.url)) {
        seen.add(d.url);
        all.push(d);
      }
    });
  } catch {}
}
fs.writeFileSync('jimeng-all.json', JSON.stringify(all, null, 2));
console.log('Total unique items:', all.length);
"
```

## 脚本工作原理

### jimeng-scraper.js

```bash
# 用法
node jimeng-scraper.js --port 9230 --output batch1.json --max 500
```

**参数：**
- `--port`：Chrome 远程调试端口（9230-9233）
- `--output`：输出 JSON 文件名
- `--max`：最大爬取条数

**工作流程（v2.0）：**
1. 连接到指定端口的 Chrome 实例
2. 导航到即梦首页（domcontentloaded，不用 networkidle）
3. 循环：
   a. 健康检查（30秒一次，打印进度/速度/错误数）
   b. 确保在首页（检测详情页自动返回）
   c. 检测页面错误（连续3次自动刷新）
   d. 用多选择器查找图片（6个备选，自动切换）
   e. 逐个点击图片 → **跳转到详情页**（整页跳转，不是弹窗）
   f. 在详情页提取提示词、模型、比例、作者、日期
   g. safeGoto 返回首页，等待图片加载
   h. 每条数据即时追加写入文件（appendFileSync，不读取整个文件）
   i. 每 50 条暂停 5-10 秒（防反爬）
4. 滚动加载更多图片（最多50次）
5. 重复直到达到 max 条数或无新内容

**防反爬措施：**
- 随机延迟：每个操作间 0.8-1.5 秒随机等待（已加速）
- 每 50 条暂停 5-10 秒（已加速）
- 使用 force click 避免被遮挡元素拦截
- URL 去重防止重复爬取

**速度优化记录（2026-05-22）：**
- `DELAY_MIN/MAX`: 2000/4000 → 800/1500
- 点击后等待: 2000-3500ms → 1200-2000ms
- 关闭弹窗等待: 1500-2500ms → 800-1200ms
- 滚动等待: 2000-4000ms → 1000-2000ms
- 批次暂停: 10-15s → 5-10s，批次大小 30→50

### 已知问题

1. **Chrome 崩溃**：有时 Chrome 会弹出崩溃提示，关掉那个窗口，重新启动该端口
2. **速度限制**：约 5-6 条/分钟/端口，4 端口并行约 20-24 条/分钟

### v2.0 修复记录

| 问题 | 修复方案 |
|------|----------|
| 详情页循环跳转 | 点击后 waitForURL 等待跳转，在详情页提取数据后 safeGoto 返回 |
| networkidle 超时 | 改用 domcontentloaded + 手动等待图片加载 |
| 文件写入 O(n²) | 改为 appendFileSync 追加模式 |
| 选择器脆弱 | 6 个备选 IMAGE_SELECTORS，自动切换 |
| goto 失败静默 | safeGoto 带 3 次重试，失败后报错退出 |
| 无限刷新循环 | MAX_REFRESHES=20，超过后退出 |
| 弹窗关闭无效 | closeModal() 智能检测，先检查再关闭 |
| 懒加载 src 为空 | getImgSrc() 同时检查 src/data-src/data-lazySrc |
| 无进度速度 | 每条打印 条/分钟 速度 |
| 无优雅退出 | Ctrl+C 安全退出，数据不丢失 |
| 无连接错误处理 | Chrome 连接失败时明确报错并退出码 1 |
| 无健康监控 | 每 30 秒打印进度/速度/错误/选择器 |

### 运行方式

**推荐：4 端口并行（后台 Bash 任务）**
```bash
cd /c/Users/Administrator/Desktop/daliy/jimeng-scraper
node jimeng-scraper.js --port 9230 --output batch1.json --max 500 &
node jimeng-scraper.js --port 9231 --output batch2.json --max 500 &
node jimeng-scraper.js --port 9232 --output batch3.json --max 500 &
node jimeng-scraper.js --port 9233 --output batch4.json --max 500 &
```

## 数据格式

每条数据的 JSON 结构：
```json
{
  "prompt": "提示词文本...",
  "model": "4.5",
  "ratio": "9:16",
  "author": "作者名",
  "date": "2026-03-01",
  "url": "https://jimeng.jianying.com/ai-tool/work-detail/...",
  "scrapedAt": "2026-05-21T14:09:03.573Z"
}
```

## 已有数据分析（1764 条）

### 模型分布
| 模型 | 数量 | 占比 |
|------|------|------|
| 3.1 | 394 | 22.3% |
| 4.5 | 345 | 19.6% |
| 4.0 | 339 | 19.2% |
| 4.1 | 243 | 13.8% |
| 3.0 | 153 | 8.7% |
| 5.0 Lite | 139 | 7.9% |
| 4.6 | 87 | 4.9% |
| 4.7 | 62 | 3.5% |
| 3 | 2 | 0.1% |

### 提示词特征
- 平均长度：202 字符
- 最短：12 字符
- 最长：878 字符
- 语言：100% 中文，63.2% 混合英文技术词

### 高频关键词 TOP 15
| 关键词 | 频次 |
|--------|------|
| 氛围感 | 264 |
| 写实 | 294 |
| 梦幻 | 301 |
| 高级感 | 196 |
| 极繁主义 | 193 |
| 视觉冲击 | 177 |
| 超清 | 169 |
| 大师杰作 | 141 |
| 古风 | 139 |
| 压迫感 | 133 |
| 极致细节 | 130 |
| 高质量 | 109 |
| 水彩 | 106 |
| 电影质感 | 78 |
| 油画 | 78 |

## Skill 优化状态

已优化的文件：
- ✅ `.claude/skills/ai-image-prompt/SKILL.md` - 更新即梦部分，添加参考文件指引
- ✅ `.claude/skills/ai-image-prompt/references/keywords.md` - 添加即梦高频词库
- ✅ `.claude/skills/ai-image-prompt/references/portrait.md` - 添加即梦人像提示词模式（819条数据）
- ✅ `.claude/skills/ai-image-prompt/references/cinematic.md` - 添加即梦电影感提示词模式（1075条数据）
- ✅ `.claude/skills/ai-image-prompt/references/realistic.md` - 添加即梦写实提示词模式（1290条数据）
- ✅ 创建 `.claude/skills/ai-image-prompt/references/jimeng.md` - 即梦专属参考文件（1764条数据）

## 下次继续时的操作

**最简方式**：把 `jimeng-scraper/RUNBOOK.md` 给 AI，AI 就知道怎么做。

**手动步骤**：
1. 检查当前数据：`node -e "console.log(JSON.parse(require('fs').readFileSync('jimeng-all.json','utf-8')).length)"`
2. 启动 Chrome（4 个端口）
3. 运行爬取（4 端口并行，每个 --max 500）
4. 合并数据到 jimeng-all.json
5. 目标 2000 条，当前 1764 条，还需 236 条

## 本次会话记录（2026-05-22）

**操作：**
- 优化了脚本速度（延迟缩减 50-60%）
- 第一轮：启动 4 个并行 agent，运行约 5 分钟，新增 92 条（366 → 458）
- 第二轮：启动 4 个后台 Bash 任务，运行约 30-45 分钟，新增 1306 条（458 → 1764）
- 总数据从 366 → 1764 条（+1398 条）

**本轮数据：**
- batch1: 835 条（+397 新增）
- batch2: 953 条（+255 新增）
- batch3: 500 条（+343 新增）
- batch4: 946 条（+226 新增）
- 去重后总计：1764 条

**发现：**
- 后台 Bash 任务比 agent 更稳定（无 10 分钟超时限制）
- 单实例约 30 分钟可爬 500 条
- `Execution context was destroyed` 错频发但脚本可自动恢复
- 部分 batch 存在重复数据（页面滚动导致同一图片被多次抓取）

**Skill 优化：**
- 创建即梦专属参考文件 `jimeng.md`（基于 1764 条数据）
- 更新人像、电影感、写实参考文件添加中文模式
- 更新 SKILL.md 添加即梦参考文件指引
- 提取高频美学词、画质词、结构模式、艺术家参考

## 注意事项

- 爬取过程中不要手动操作 Chrome 窗口
- 如果某个 Chrome 崩溃了，关掉崩溃提示窗口，重新启动该端口的 Chrome
- 脚本会自动处理大部分错误，但偶尔需要手动干预
- 数据是即时写入的，即使中断也不会丢失已爬取的数据
