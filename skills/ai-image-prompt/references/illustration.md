# 插画/卡通风格提示词参考

> 适用于插画风格、卡通角色、信息图、数字拼贴等场景。

## 数据特征

- 插画：平均 1696 字符，英文为主（90%）
- 卡通：平均 2621 字符（最长的类型），多为分阶段指令
- 核心词：brand, illustration, editorial, visual, style, clean

## 常见结构模式

### 模式 1：分阶段指令式（卡通类最常见）

```
PHASE 1: CONCEPTUAL FRAMEWORK
Create a dynamic digital collage that merges [风格A] with [风格B].

This is controlled rebellion — a composition that feels spontaneous, energetic, and expressive while maintaining strong brand coherence.

Aesthetic direction:
- Anti-polished
- Raw textures
- Layered imperfections
- Youth-driven visual noise

PHASE 2: MODEL & PHOTOGRAPHY
[人物/产品描述]

PHASE 3: COLOR BLOCKING
[色彩方案]

PHASE 4: GRAPHIC ELEMENTS
[图形元素]

PHASE 5: TYPOGRAPHY
[文字排版]

PHASE 6: TEXTURE & BACKGROUND
[材质和背景]
```

### 模式 2：JSON 结构化（插画类常见）

```json
{
  "type": "promotional banner design set",
  "theme": "strawberry advertisement campaign",
  "style": "anime illustration, bright, cheerful, commercial graphic design",
  "color_palette": "pastel pink, strawberry red, cream white",
  "elements": ["strawberry", "cream", "sparkles", "ribbon"]
}
```

### 模式 3：混合媒体描述

```
Fusion of hyper-realistic photography and graphic illustration, seamless integration between subject and cartoon. Add graphic overlay elements: doodle arrows, scribbles, racing-themed abstract shapes, speed lines, comic-style symbols.
```

## 高频关键词

| 类别 | 关键词 |
|------|--------|
| 风格 | illustration, digital art, collage, mixed media, editorial |
| 元素 | graphic elements, doodle, scribbles, stickers, badges |
| 色彩 | bold colors, vibrant, neon, pastel, color blocking |
| 质感 | raw textures, paper texture, grain, noise, hand-drawn |
| 排版 | typography, hand-lettering, bold text, overlay |

## 插画风格速查

| 风格 | 特征 | 适用场景 |
|------|------|----------|
| 扁平插画 | 简洁色块，无阴影 | 信息图、UI设计 |
| 噪点插画 | 有颗粒感，复古 | 海报、书籍封面 |
| 3D插画 | 立体感，卡通渲染 | 游戏、广告 |
| 拼贴风 | 多元素拼接，层次感 | 社交媒体、创意广告 |
| 像素风 | 复古游戏感 | 怀旧主题、游戏相关 |
| 线稿风 | 手绘线条，简洁 | 教育、说明图 |

## 完整示例

### 时尚拼贴
```
Full-body fashion editorial shot of a confident young woman, fusion of hyper-realistic photography and graphic illustration, seamless integration between subject and cartoon. Add graphic overlay elements: doodle arrows, scribbles, racing-themed abstract shapes, speed lines, comic-style symbols, dynamic motion lines, checkered flag doodles.

Background: bright indoor motorsport garage pit lane setting with large industrial windows flooding soft diffused daylight, glossy reflective concrete floor.

High contrast, HDR lighting, sharp focus, fashion editorial motorsport composition, surreal mixed-media aesthetic, ultra-detailed, 8K resolution.
```

### 美食信息图
```
Create step-by-step recipe infographic for creamy garlic mushroom pasta, top-down view, minimal style on white background, ingredient photos labeled: "200g spaghetti", "150g mushrooms", "3 garlic cloves", "200ml cream", "1 tbsp olive oil", "parmesan", "parsley", dotted lines showing process steps with icons (boiling pot, sauté pan, mixing), final plated pasta shot at the bottom.
```

### 动漫风格
```
Anime-style illustration of [CHARACTER], vibrant colors, dynamic pose, detailed background with cherry blossoms falling. Soft cel-shading with gradient shadows. Studio Ghibli inspired color palette, warm and inviting atmosphere. High detail, clean linework, 4K resolution.
```

## 色彩搭配推荐

| 主题 | 配色方案 |
|------|----------|
| 赛博朋克 | neon pink + electric blue + dark purple |
| 复古怀旧 | warm orange + teal + cream |
| 自然清新 | sage green + soft pink + cream |
| 高端奢华 | gold + black + white |
| 活力青春 | bright yellow + coral + sky blue |
