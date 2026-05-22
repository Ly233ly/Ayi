# 电影感/广告风格提示词参考

> 适用于电影级画面、品牌广告、生活方式摄影等场景。

## 数据特征

- 平均长度：1300 字符
- 语言：以英文为主（75%），部分 JSON 格式（25%）
- 核心词：cinematic, lighting, depth, motion, realistic, photography

## 常见结构模式

### 模式 1：段落式详细描述（最常见）

```
[风格/类型] + [主体详细描述] + [姿态/动作] + [服装/配饰] + [背景] + [光影] + [氛围] + [画质]
```

**示例**：
```
Avant-garde sports fashion advertisement, oversized tennis racket positioned like monumental sculpture, female athlete seated casually on the strings as if a suspended lounge, giant word "PRECISION" in bold typography behind, crisp white studio backdrop, reflective court-like floor, luxury sportswear editorial aesthetic, cinematic lighting, ultra-clean composition, 1:1
```

### 模式 2：分阶段指令式（复杂商业场景）

```
PHASE 1: 概念框架 — 整体风格和情绪方向
PHASE 2: 主体描述 — 人物/产品的具体细节
PHASE 3: 构图与镜头 — 角度、景深、画面布局
PHASE 4: 光影与氛围 — 光源、色调、环境效果
PHASE 5: 材质与细节 — 表面质感、反射、纹理
PHASE 6: 背景与环境 — 场景、道具、空间感
PHASE 7: 技术参数 — 输出规格
```

### 模式 3：JSON 结构化

```json
{
  "style": "cinematic realism, surreal moment frozen in time",
  "scene": "a suburban street with muted yellow walls",
  "subject": { "type": "young woman", "appearance": "..." },
  "camera": { "angle": "slight low angle", "lens": "85mm" },
  "lighting": "soft diffused daylight",
  "mood": "nostalgic, contemplative"
}
```

## 高频关键词

| 类别 | 关键词 |
|------|--------|
| 风格 | cinematic, editorial, luxury, premium, avant-garde |
| 光影 | dramatic lighting, soft lighting, rim light, volumetric light |
| 构图 | composition, depth of field, bokeh, shallow depth |
| 氛围 | motion, dynamic, energy, atmosphere, mood |
| 画质 | ultra-realistic, sharp focus, high contrast, 4K |

## 商业场景常用短语

| 场景 | 常用表达 |
|------|----------|
| 产品广告 | "premium product photography", "commercial lighting", "studio shot" |
| 时尚海报 | "fashion editorial", "luxury campaign", "high-fashion magazine aesthetic" |
| 品牌宣传 | "brand identity", "lifestyle advertising", "premium aesthetic" |
| 运动场景 | "dynamic action", "athletic energy", "powerful movement" |
| 美食摄影 | "food photography", "appetizing", "fresh ingredients" |

## 完整示例

### 运动鞋广告
```
A cinematic, high-end sneaker advertisement poster featuring a young male model mid-air in a dynamic jumping pose, captured from a low-angle perspective to emphasize power and motion. The model is wearing a coordinated beige streetwear outfit (hoodie and joggers), with oversized chunky white sneakers that have bold orange accents on the sole and side stripes.

The background is a smooth studio gradient in warm tones, blending light yellow and vibrant orange for an eye-catching, energetic feel. Dramatic soft studio lighting enhances the subject, with glowing highlights and subtle shadows that complement the outfit and colour palette.

Behind the model, large bold typography is seamlessly integrated into the composition, reading "RISE" in oversized modern sans-serif font, partially obscured by the subject for depth.

Ultra-realistic detail, sharp focus, high contrast, commercial fashion photography style, magazine-quality composition, 4K resolution.
```

### 香水广告
```
Create a hyper-realistic cinematic luxury perfume product photograph featuring [PERFUME BOTTLE DESIGN] positioned in [COMPOSITION / ANGLE] within a dramatic elemental environment of [ELEMENTAL SETTING: water, smoke, ice, firelight, forest, florals, spices, gemstones].

The bottle should feel premium and tactile, with [MATERIAL DETAILS: glossy glass, metallic cap, gold label, transparent liquid, frosted surface, engraved text], sharp reflections, realistic refactions, and crisp readable branding: [BRAND / LABEL TEXT].

Surround the product with carefully arranged sensory ingredients. Cinematic lighting, ultra-realistic detail, commercial photography style.
```

## 画质增强组合

```
ultra-realistic, sharp focus, high contrast, cinematic lighting, 4K resolution
```
```
studio-grade sharpness, high dynamic range, professional photography
```
```
editorial quality, magazine-worthy, commercial grade, premium finish
```

## 即梦中文电影感模式

> 基于 1075 条即梦电影感数据分析

### 常见结构
```
[风格/艺术家]，[场景描述]，[主体/人物]，[光影效果]，[色调]，[氛围描述]，[构图方式]，[画质词]
```

### 电影感高频词
- 氛围：氛围感、电影质感、叙事感、故事感
- 光影：明暗对比强烈、阴影过渡自然、质感光照、自然光线
- 构图：电影级构图、超广角构图、对角线构图
- 画质：8K画质、超清、极致细节、视觉冲击力强

### 电影感画质组合
```
电影级构图，视觉冲击，8K画质，超清，极致细节，明暗对比强烈，阴影过渡自然
```

### 即梦电影感示例
```
极繁主义风格，华丽炫酷的花纹和质感、冷色调，整个画面散发出一种美轮美奂的诡异气质，惊艳迷人却又令人感觉到危险和恐惧，极致的细节刻画，极致的立体纹理，奢华、繁琐、恢弘、大气，超高清画质。超广角构图，张力十足，压迫感，细节生动完美。极其震撼的一幕，视觉冲击力强，明暗对比强烈，阴影过渡自然，电影级构图，视觉冲击，8K画质
```
