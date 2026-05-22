---
name: ai-image-prompt
description: 为即梦、GPT Image 2、NanoBanana、Midjourney、Stable Diffusion等AI图像生成平台编写和优化提示词。当用户提到AI生图、写提示词、prompt优化、图片生成、Midjourney、Stable Diffusion、即梦、DALL-E、文生图、画图、生图等场景时必须使用此技能。即使用户没有明确说"写提示词"，只要涉及AI图像生成相关需求，都应该主动调用此技能。
---

# AI图像生成提示词技能

帮助用户为各种AI图像生成平台编写高质量、精准的提示词。

## 核心原则

1. **描述"有什么"而不是"没有什么"** — AI理解否定词有困难，用加法代替减法
2. **具体化材质和光效** — 不要说"好看"，要说具体的材质和光效描述
3. **词缀顺序很重要** — 从左到右权重递减，重要的放前面
4. **不同平台用不同写法** — 即梦、GPT Image 2、NanoBanana、SD各有特点
5. **详细胜过简略** — 高质量提示词通常 500-2000 字符，包含构图、光影、材质、氛围等细节

## 提示词结构公式

### 基础公式

```
主体 + 场景 + 风格 + 光线 + 构图 + 画质词 + 背景
```

### 进阶公式

```
主体(特征/姿态) + 艺术风格 + 材质质感 + 光影 + 镜头视角 + 画质 + 色彩 + 背景 + 负面提示词
```

### 各要素权重

| 要素 | 重要性 | 说明 |
|------|--------|------|
| 主体 | ⭐⭐⭐⭐⭐ | 画面核心，必须清晰明确，放最前面 |
| 风格 | ⭐⭐⭐⭐⭐ | 决定整体调性，紧随主体 |
| 角度/构图 | ⭐⭐⭐⭐⭐ | 决定画面构图，影响最大 |
| 光影 | ⭐⭐⭐⭐ | 影响氛围和质感 |
| 材质 | ⭐⭐⭐ | 增加细节真实感 |
| 氛围 | ⭐⭐⭐ | 锦上添花 |
| 画质词 | ⭐⭐ | 提升整体质量（SD有效，其他平台可选） |

## 不同平台写法

### 即梦AI
- 中文为主，可混合英文技术词（63.2%用户这样做）
- 平均长度 200 字符左右，包含风格+主体+细节+光影+画质词
- 高频美学词：氛围感(264)、细腻(423)、精致(277)、高级感(196)、极繁主义(193)
- 画质词：8K、超高清、32K、壁纸级精度
- 括号用法：仅作补充说明（艺术家名、材质、翻译），不支持 `((关键词))` 加权语法
- 强调关键词：通过重复使用或放在更前面实现

**结构公式**：`[风格/艺术家] + [主体描述] + [细节/材质] + [光影/色调] + [构图/视角] + [氛围/情绪] + [画质词]`

**细节要求**：
- 色彩要具体：不要"好看的颜色"，要"紫蓝粉交织的霓虹色彩"
- 材质要具体：不要"漂亮的瓶子"，要"切割棱面玻璃瓶身，琥珀色液体"
- 光影要具体：不要"好看的光"，要"柔和侧光勾勒边缘光与高光反射"

**简短示例**：
```
赛博朋克风格，雨夜都市，霓虹灯牌高悬于摩天大楼之间，雨水倾泻在潮湿的街道上形成镜面倒影，体积光穿透雨幕，低角度仰拍，氛围感拉满，8K超高清画质
```

**完整示例**：
```
高级感香水产品摄影，一瓶晶莹剔透的切割棱面玻璃香水瓶，琥珀色香水液体在光线中流转，金色瓶盖雕琢精致，瓶身细腻纹理清晰可见，质感十足。黑色丝绒背景，柔和侧光勾勒出边缘光与高光反射，暖金色调，明暗对比强烈，阴影过渡自然。低角度特写构图，极具高级感与电影质感，视觉冲击力强。极致细节刻画，细腻精致，8K超高清画质，壁纸级精度，大师级商业摄影
```

> 详细即梦提示词模式、高频词库、分类模板请查阅 `references/jimeng.md`

### GPT Image 2
- 详细描述，英文长句，具体到相机位置和参数

```
Extreme low angle worm's eye view, camera directly below looking up, dark red smartphone entering from bottom-left diagonally toward upper-right, phone back with dual camera rings visible, crashing into white irregular ice block in upper-right, ice shattering into fragments, ice island platform below, dark gray gradient background, cold mist rising, dramatic rim lighting on phone edge
```

### NanoBanana
- 中文精简，核心元素即可

```
虫眼视角仰拍,手机从左下角斜向上冲出撞击右上方冰块,冰块碎裂,冰面地面,灰色渐变背景,冷气雾气,边缘光,产品广告风格
```

### Stable Diffusion
- 支持正向+负向提示词，英文，括号权重

**正向**：
```
(best quality:1.2), ((masterpiece)), dark red smartphone, (extreme low angle:1.3), crashing into white ice block, ice shattering, dramatic rim lighting, volumetric light, 3D render
```

**负向**：
```
blurry, low quality, plastic, flat lighting, cartoon, deformed, watermark, text, bad anatomy
```

### Midjourney
- 支持参数控制，可用 --ar、--v 等

```
dark red smartphone crashing into white ice block, extreme low angle worm's eye view, ice shattering, dramatic rim lighting, 3D product render --ar 16:9 --v 6
```

## 权重控制

### SD 权重语法
```
(word:1.3)   # 权重1.3，加强
(word:0.8)   # 权重0.8，减弱
((word))     # 约等于1.21权重
(((word)))   # 约等于1.33权重
```

### 即梦 权重语法
```
(关键词)     # 轻微加强
((关键词))   # 强烈加强
```

### MJ 权重语法
```
word::1.3    # 权重1.3
word::2      # 权重2
```

## 画面质量词（SD专用）

| 类型 | 关键词 |
|------|--------|
| 高质量 | best quality, masterpiece, HDR, UHD |
| 高分辨率 | 8K, 4K, ultra-detailed |
| 渲染引擎 | unreal engine, octane render, cinema 4D |
| 摄影风格 | professional lighting, sharp focus, realistic shadows |

## 工作流程

1. 询问用户使用哪个平台（即梦/GPT Image 2/NanoBanana/SD/MJ/其他）
2. 了解用户想要的画面内容和类型
3. **根据画面类型查阅对应的参考文件**（见下方分类指引）
4. 按照结构公式组织提示词
5. 根据平台特点调整写法
6. 提供优化建议

## 画面类型分类指引

根据用户需求的画面类型，查阅对应的参考文件获取详细模式和示例：

| 类型 | 参考文件 | 说明 |
|------|----------|------|
| **即梦AI专属** | `references/jimeng.md` | **即梦平台中文提示词模式、高频词、模板（基于1764条真实数据）** |
| 电影感/广告 | `references/cinematic.md` | 电影级画面、品牌广告、生活方式 |
| 写实/产品 | `references/realistic.md` | 超写实摄影、产品展示、材质细节 |
| 人像/肖像 | `references/portrait.md` | 人物肖像、角色设计、时尚编辑 |
| 3D/渲染 | `references/3d.md` | 3D渲染、产品建模、科技感 |
| 海报/排版 | `references/poster.md` | 海报设计、文字排版、品牌视觉 |
| 电商/商业 | `references/ecommerce.md` | 电商主图、详情页、促销物料 |
| 插画/卡通 | `references/illustration.md` | 插画风格、卡通角色、信息图 |
| 通用关键词 | `references/keywords.md` | 角度、光影、材质、氛围词库 |

**使用方式**：
- **即梦平台**：优先查阅 `references/jimeng.md`，包含中文美学词汇、高频模式、完整模板
- 其他平台：根据类型查阅对应参考文件，类型不明确时先询问用户

## 常见问题解决

| 问题 | 解决方法 |
|------|----------|
| 角度不对 | 明确写出相机位置，如"虫眼视角仰拍"，可加权重 |
| 材质模糊 | 细化描述，如"金属磨砂边框+玻璃背板" |
| 光影平淡 | 加入具体光效，如"边缘光、体积光" |
| 氛围单薄 | 添加环境元素，如"冷气弥漫、冰雾升腾" |
| 构图混乱 | 指定构图方式，如"对角线构图" |
| 主体不突出 | 将主体放最前面，增加权重 |
