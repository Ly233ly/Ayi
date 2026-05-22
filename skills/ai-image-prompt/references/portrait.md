# 人像/肖像风格提示词参考

> 适用于人物肖像、角色设计、时尚编辑、K-Pop风格等场景。

## 数据特征

- 平均长度：1435 字符
- 语言：英文为主（82%），JSON（17%）
- 核心词：portrait, face, skin, soft lighting, cinematic, style

## 常见结构模式

### 模式 1：JSON 结构化人像（K-Pop/时尚类常见）

```json
{
  "configuration": {
    "format": "Mirror-Selfie Portrait",
    "target_resolution": "8K UHD",
    "style_preset": "K-Pop Idol Aesthetic / Y2K Colorful"
  },
  "subject_profile": {
    "biometrics": { "ethnicity": "...", "age_range": "..." },
    "hair": { "style": "...", "color": "..." },
    "makeup": { "style": "...", "details": "..." }
  },
  "outfit": { "top": "...", "bottom": "...", "accessories": "..." },
  "lighting": { "type": "...", "color_temperature": "..." },
  "background": { "type": "...", "details": "..." }
}
```

### 模式 2：段落式描述（编辑类常见）

```
[场景描述] + [人物外貌] + [服装] + [姿态] + [光影] + [氛围] + [画质]
```

**示例**：
```
Tokyo nightlife editorial. Full body shot, low angle looking up slightly. A cool, alluring young woman is resting her lower back against the hood of a modified pink sports car. She has long, wavy, multi-colored hair (pink/cyan/blonde), catching the city lights. Wearing a cropped leather jacket and high-waisted pants. Neon-lit urban background, cinematic lighting, editorial photography style.
```

## 高频关键词

| 类别 | 关键词 |
|------|--------|
| 人像 | portrait, face, facial features, skin, expression |
| 光影 | soft lighting, natural light, studio lighting, rim light |
| 风格 | editorial, fashion, cinematic, magazine, luxury |
| 细节 | sharp focus, high detail, skin texture, makeup |
| 背景 | bokeh, blurred background, studio backdrop, urban |

## 人像描述要素

### 面部特征
- 脸型：oval face, round face, angular jawline, sharp cheekbones
- 眼睛：deep-set eyes, almond-shaped, bright pupils, intense gaze
- 嘴唇：full lips, thin lips, natural pink, glossy
- 皮肤：fair skin, olive skin, smooth complexion, natural glow

### 发型
- 长发：long flowing hair, wavy hair, straight hair, curly hair
- 短发：pixie cut, bob cut, slicked back
- 颜色：blonde, brunette, pink highlights, multi-colored

### 姿态
- 站姿：confident stance, relaxed pose, power pose
- 坐姿：casual sitting, elegant seated, leaning back
- 动态：walking, turning, looking over shoulder

## 完整示例

### 时尚编辑人像
```
Full-body fashion editorial shot of a confident young woman with long wavy dark brown hair, striking sharp facial features, defined cheekbones, deep-set eyes with a calm dominant gaze, sunglasses perched on top of her head, standing in a powerful pose — one hand resting on an open scissor door, body slightly turned, looking straight at camera with a composed, fierce expression.

Wearing a fitted black long-sleeve racing jersey with gold sponsor logos, black racing gloves, with a white, black, and red Sparco racing suit draped and hanging off her body, and black racing shoes. Clean editorial styling, natural confident stance, wind slightly moving her dark wavy hair.

Background: bright indoor motorsport garage pit lane setting with large industrial windows flooding soft diffused daylight, glossy reflective concrete floor.

High contrast, HDR lighting, sharp focus, fashion editorial motorsport composition, ultra-detailed, 8K resolution.
```

### K-Pop 风格
```
Create a high-resolution vertical character concept poster with a luxury pink and white aesthetic, blending elegance with edgy, modern fashion. The layout should feel like a premium magazine profile with clean sections and perfect grid alignment.

Main subject: A unique young woman (not resembling any real person), with long silky dark hair featuring subtle pink highlights. She has a confident, calm expression with a slightly mysterious aura. She wears a black and pink fusion outfit (mix of streetwear and idol fashion) with glossy textures, lace, and metallic accents.

Lighting is soft but dramatic, with a pink-tinted key light from the left and cool fill light from the right. Background is a gradient from soft pink to white with subtle geometric patterns.

Editorial quality, magazine-worthy, premium finish, 8K resolution.
```

## 光影推荐

| 场景 | 光影方案 |
|------|----------|
| 时尚编辑 | dramatic rim lighting + high contrast + editorial shadows |
| K-Pop/甜美 | soft pink key light + cool fill + dreamy glow |
| 暗黑风格 | neon lighting + deep shadows + cyberpunk colors |
| 自然人像 | golden hour + warm tones + soft bokeh |
| 商业人像 | studio lighting + clean background + professional finish |

## 即梦中文人像模式

> 基于 819 条即梦人像数据分析

### 常见结构
```
[风格]风格，[人物外貌描述]，[服装/配饰]，[姿态/表情]，[光影效果]，[色调]，[背景]，[画质词]
```

### 面部描述高频词
- 皮肤：皮肤白皙、水润有光泽、光滑细腻
- 眼睛：桃花眼、眼尾微微上翘、深邃眼神、灵动
- 嘴唇：嘟嘟唇、水润有光泽、自然唇色
- 鼻子：翘鼻、高鼻梁

### 人像画质组合
```
写真摄影风格，低饱和度色调，大师级笔触油画，质感光照，自然光线，质感十足，电影级别镜头，高清超高清画质
```

### 即梦人像示例
```
一位皮肤白皙、有着翘鼻、水润有光泽的嘟嘟唇、俏丽桃花眼且眼尾微微上翘、画着长长眼线的古风CG风格魔法少年，身着材质上乘、绣有纹理清晰暗纹的纱质轻盈飘逸服饰，黑色长发，背景模糊干净，写真摄影风格，低饱和度色调，大师级笔触油画，质感光照，自然光线，质感十足，电影级别镜头，高清超高清画质
```
