# 即梦提示词爬取指南

> 最后更新：2026-05-22
> 当前进度：1764 条去重数据（目标 2000 条，还需 236 条）

## 项目概述

从即梦网站（jimeng.jianying.com）批量爬取用户生成图片的提示词，用于优化 `ai-image-prompt` skill。

## 文件结构

```
C:\Users\Administrator\Desktop\daliy\scripts\
├── jimeng-scraper.js          # 爬取脚本（核心）
├── jimeng-scraper-guide.md    # 本指南文件
├── jimeng-all.json            # 合并后的去重数据（当前 458 条）
├── batch1.json                # Agent 1 爬取结果（累计 79 条）
├── batch2.json                # Agent 2 爬取结果（累计 56 条）
├── batch3.json                # Agent 3 爬取结果（累计 213 条）
├── batch4.json                # Agent 4 爬取结果（累计 254 条）
├── package.json               # Node.js 依赖
└── node_modules/              # 依赖目录（已安装 playwright）
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

**工作流程：**
1. 连接到指定端口的 Chrome 实例
2. 导航到即梦首页
3. 循环：
   a. 获取当前页面所有图片元素
   b. 逐个点击图片（force click 绕过遮挡）
   c. 等待弹窗加载
   d. 用 JavaScript 从 DOM 提取：
      - 提示词（找"图片提示词"标签后的文本）
      - 模型版本（找"图片 X.X"格式）
      - 比例（找"X:X"格式）
      - 作者和日期
   e. 按 Escape 关闭弹窗
   f. 每条数据即时写入文件（防止中断丢失）
   g. 随机延迟 2-4 秒（防反爬）
4. 滚动加载更多图片
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

1. **Agent 超时**：Claude 的后台 agent 有超时限制（约 10 分钟），每个 agent 大约能爬 100-200 条就被终止
2. **Chrome 崩溃**：有时 Chrome 会弹出崩溃提示，可以关掉那个窗口，不影响其他端口
3. **写入失败**：脚本的追加写入机制偶尔会失败（被 catch 静默忽略），导致部分数据在内存中丢失

### Bug 修复记录（2026-05-22）

**v2.0 重写修复（全部问题）：**

| 问题 | 修复方案 |
|------|----------|
| 详情页循环跳转 | URL 检测 + DOM 双重检测，自动返回首页 |
| 弹窗检测假阳性 | 5 个备选 DETAIL_SELECTORS，检测 offsetParent/visibility |
| 文件写入竞争 | 改为 appendFileSync 追加模式，不读取整个文件 |
| 选择器脆弱 | 6 个备选 IMAGE_SELECTORS，自动切换 |
| goto 失败静默 | safeGoto 带 3 次重试，失败后报错 |
| 无限刷新循环 | MAX_REFRESHES=20，超过后退出 |
| dialog.close() 无效 | closeModal() 用 4 种方式关闭（Escape/点击空白/移除DOM/再Escape）|
| 懒加载 src 为空 | getImgSrc() 同时检查 src/data-src/data-lazySrc |
| goBack() 导航错误 | 统一用 safeGoto(HOME_URL) |
| 滚动次数太少 | MAX_SCROLL_COUNT 从 20 提高到 50 |
| 无进度速度 | 每条打印 条/分钟 速度 |
| 无优雅退出 | SIGINT handler，安全退出并保存数据 |
| 无连接错误处理 | Chrome 连接失败时明确报错并退出 |

### 解决方案

如果需要爬取更多数据（比如 2000 条），可以：

**方案 A：多轮运行**
- 每轮启动 4 个 agent，每个爬 200 条
- 重复多轮直到达到目标
- 每轮结束后合并数据

**方案 B：直接在终端运行（推荐）**
- 打开 4 个终端窗口
- 每个窗口运行一个脚本实例：
```bash
# 终端 1
cd /c/Users/Administrator/Desktop/daliy/scripts
node jimeng-scraper.js --port 9230 --output batch1.json --max 500

# 终端 2
cd /c/Users/Administrator/Desktop/daliy/scripts
node jimeng-scraper.js --port 9231 --output batch2.json --max 500

# 终端 3
cd /c/Users/Administrator/Desktop/daliy/scripts
node jimeng-scraper.js --port 9232 --output batch3.json --max 500

# 终端 4
cd /c/Users/Administrator/Desktop/daliy/scripts
node jimeng-scraper.js --port 9233 --output batch4.json --max 500
```
- 这样不受 agent 超时限制

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

1. **读取本文件**：让 Claude 读取 `jimeng-scraper-guide.md`
2. **检查当前数据**：查看 `jimeng-all.json` 有多少条
3. **启动 Chrome**：运行上面的 Chrome 启动命令
4. **继续爬取**：告诉 Claude 继续爬取到 2000 条（还需约 236 条）
5. **合并数据**：爬取完成后合并新旧数据
6. **优化 Skill**：基于更多数据进一步优化提示词 skill

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
