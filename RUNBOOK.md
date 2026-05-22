# Skills 运行手册

> 把这个文件给 AI，AI 就知道该做什么、怎么做。

## 仓库是什么

GitHub 仓库 `Ly233ly/Ayi` 用于存放 Claude Code 的技能（skills）和爬虫脚本（scrapers）。

```
Ayi/
├── skills/          ← Claude 技能
│   ├── ai-image-prompt/
│   ├── chrome-cookie-decryptor/
│   └── personal-finance/
└── scrapers/        ← 爬虫脚本
    └── jimeng-scraper/
```

## Skills 目录结构

每个 skill 标准结构：
```
skill-name/
├── SKILL.md          ← 必须，技能主文件（含 YAML frontmatter）
├── references/       ← 可选，参考资料（按需加载）
│   ├── topic-a.md
│   └── topic-b.md
└── scripts/          ← 可选，可执行脚本
    └── helper.py
```

## 已有 Skills

| 名称 | 用途 | 路径 |
|------|------|------|
| ai-image-prompt | AI图像生成提示词（即梦/MJ/SD/GPT） | `skills/ai-image-prompt/` |
| chrome-cookie-decryptor | Chrome Cookie 提取解密 | `skills/chrome-cookie-decryptor/` |
| personal-finance | 个人财务分析（钱迹CSV） | `skills/personal-finance/` |

## 你要做什么

### 上传新 skill 到 GitHub

```bash
# 1. 克隆仓库
cd /tmp && rm -rf ayi-check && git clone --depth 1 https://github.com/Ly233ly/Ayi.git ayi-check

# 2. 复制 skill 文件
cp -r /path/to/your-skill /tmp/ayi-check/skills/your-skill/

# 3. 提交并推送
cd /tmp/ayi-check
git add skills/your-skill/
git commit -m "feat: add your-skill"
git push origin main
```

### 更新已有 skill

```bash
# 1. 克隆仓库
cd /tmp && rm -rf ayi-check && git clone --depth 1 https://github.com/Ly233ly/Ayi.git ayi-check

# 2. 修改文件
# 编辑 /tmp/ayi-check/skills/xxx/SKILL.md 或 references/ 下的文件

# 3. 提交并推送
cd /tmp/ayi-check
git add skills/xxx/
git commit -m "update: xxx skill 改进说明"
git push origin main
```

### 上传新爬虫到 GitHub

```bash
# 1. 克隆仓库
cd /tmp && rm -rf ayi-check && git clone --depth 1 https://github.com/Ly233ly/Ayi.git ayi-check

# 2. 复制爬虫文件
cp -r /path/to/your-scraper /tmp/ayi-check/scrapers/your-scraper/

# 3. 更新 scrapers/README.md 索引

# 4. 提交并推送
cd /tmp/ayi-check
git add scrapers/
git commit -m "feat: add your-scraper"
git push origin main
```

## 本地 Skill 位置

| 位置 | 说明 |
|------|------|
| `C:\Users\Administrator\.claude\skills\` | 全局 skill（所有项目可用） |
| `C:\Users\Administrator\Desktop\daliy\.claude\skills\` | 项目级 skill（仅本项目） |

项目级优先于全局级。

## SKILL.md 格式

```yaml
---
name: skill-name
description: 触发描述（什么时候用这个技能）
---

# 技能标题

技能正文...
```

**description 很重要** — 它决定 Claude 什么时候触发这个技能。要写得"主动"一点，覆盖用户可能的各种说法。

## references/ 文件

- 放参考资料，按需读取，不占主上下文
- 超过 300 行的文件加目录
- 在 SKILL.md 中明确引用：`查阅 references/xxx.md`
