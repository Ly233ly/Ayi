# Skills 运行手册

> 把这个文件给 AI，AI 就知道该做什么、怎么做。

## 已有 Skills

| 名称 | 用途 | 触发场景 |
|------|------|----------|
| ai-image-prompt | AI图像生成提示词 | 写提示词、AI生图、即梦、MJ、SD、DALL-E |
| chrome-cookie-decryptor | Chrome Cookie 提取解密 | 提取Cookie、拿登录态、爬虫登录 |
| personal-finance | 个人财务分析 | 钱迹、记账分析、账单分析、CSV |

## 你要做什么

### 上传新 skill

```bash
# 1. 克隆
cd /tmp && rm -rf ayi-check && git clone --depth 1 https://github.com/Ly233ly/Ayi.git ayi-check

# 2. 复制（保持标准结构）
cp -r /path/to/skill /tmp/ayi-check/skills/skill-name/

# 3. 推送
cd /tmp/ayi-check && git add skills/skill-name/ && git commit -m "feat: add skill-name" && git push origin main
```

### 更新已有 skill

```bash
# 1. 克隆
cd /tmp && rm -rf ayi-check && git clone --depth 1 https://github.com/Ly233ly/Ayi.git ayi-check

# 2. 修改文件（SKILL.md、references/、scripts/）

# 3. 推送
cd /tmp/ayi-check && git add skills/xxx/ && git commit -m "update: xxx 说明" && git push origin main
```

## 标准结构

```
skill-name/
├── SKILL.md          ← 必须，主文件
├── references/       ← 可选，参考资料（按需加载）
│   └── xxx.md
└── scripts/          ← 可选，可执行脚本
    └── helper.py
```

## SKILL.md 模板

```yaml
---
name: skill-name
description: 触发描述（覆盖用户各种说法，写主动一点）
---

# 技能标题

技能正文...
```

## 本地 Skill 位置

| 位置 | 优先级 |
|------|--------|
| 项目级：`项目/.claude/skills/` | 高 |
| 全局级：`~/.claude/skills/` | 低 |

## 注意事项

- description 决定触发时机，要写得"主动"
- references 超过 300 行加目录
- SKILL.md 控制 500 行以内
- 数据文件、node_modules 不上传
