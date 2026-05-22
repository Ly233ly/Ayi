# AI图像生成提示词详细参考

> 本文件为索引文件，包含详细参考信息的导航。请根据需要查阅相关章节。

## 目录

1. [提示词结构详解](#提示词结构详解)
2. [权重控制完整指南](#权重控制完整指南)
3. [各平台最佳实践](#各平台最佳实践)
4. [分类参考文件](#分类参考文件)

---

## 提示词结构详解

### 核心逻辑（SD提示词顺序）

SD提示词撰写的大体逻辑：

```
画面质量 → 风格 → 元素 → 细节
```

- **若想明确某主体**：主体放前面，权重提高
- **若想明确风格**：风格词缀优于内容词缀

### 新手基础公式

```
主体 + 场景 + 风格 + 光线 + 构图 + 画质词 + 背景
```

### 进阶专业公式

```
主体(特征/姿态) + 艺术风格 + 材质质感 + 光影 + 镜头视角 + 画质 + 色彩 + 背景 + 负面提示词
```

### 词缀拆分示例

一串长的提示词可以拆分为：

```
· 画面质量: best quality, masterpiece, HDR, UHD, 8K
· 风格: ((oil_painting))
· 主要元素: princess, oval face, dancing, smile, bright pupils
· 细节: Movie light, elves, floating light points, dreams, magic
```

---

## 权重控制完整指南

### Stable Diffusion 权重语法

| 语法 | 效果 | 说明 |
|------|------|------|
| `(word:1.3)` | 权重1.3 | 精确控制加强 |
| `(word:0.8)` | 权重0.8 | 精确控制减弱 |
| `((word))` | 约1.21权重 | 双括号加强 |
| `(((word)))` | 约1.33权重 | 三括号更强加强 |
| `[word1\|word2]` | 随机选择 | 每步随机选一个 |

### 即梦AI 权重语法

| 语法 | 效果 |
|------|------|
| `(关键词)` | 轻微加强 |
| `((关键词))` | 强烈加强 |

### Midjourney 权重语法

| 语法 | 效果 |
|------|------|
| `word::1.3` | 权重1.3 |
| `word::2` | 权重2 |

---

## 各平台最佳实践

### 即梦AI
- 简洁关键词，5-8个最佳
- 逗号分隔
- 可用括号加权

### GPT Image 2
- 详细描述，具体到相机位置
- 英文长句
- 包含相机参数

### NanoBanana
- 中文精简
- 核心元素即可

### Midjourney
- 支持参数控制
- 可用 --ar 指定比例
- 可用 --v 指定版本
- 支持 :: 权重语法

### Stable Diffusion
- 支持正向和负向提示词
- 可用括号精确权重控制
- 需要更多细节描述
- 画面质量词有效

---

## 分类参考文件

根据画面类型查阅对应的详细参考：

| 类型 | 文件 | 说明 |
|------|------|------|
| 电影感/广告 | `cinematic.md` | 电影级画面、品牌广告、生活方式 |
| 写实/产品 | `realistic.md` | 超写实摄影、产品展示、材质细节 |
| 人像/肖像 | `portrait.md` | 人物肖像、角色设计、时尚编辑 |
| 3D/渲染 | `3d.md` | 3D渲染、产品建模、科技感 |
| 海报/排版 | `poster.md` | 海报设计、文字排版、品牌视觉 |
| 电商/商业 | `ecommerce.md` | 电商主图、详情页、促销物料 |
| 插画/卡通 | `illustration.md` | 插画风格、卡通角色、信息图 |
| 通用关键词 | `keywords.md` | 角度、光影、材质、氛围词库 |

---

## 调试技巧

### 问题：角度不对
**解决**：明确写出相机位置并加权重
```
❌ 低角度拍摄
✅ (extreme low angle:1.3), (worm's eye view:1.2), camera directly below looking up
```

### 问题：材质模糊
**解决**：细化材质描述并加权重
```
❌ 手机
✅ dark red smartphone, (metallic matte frame:1.2), (glass back panel:1.1), edge highlight reflection
```

### 问题：光影平淡
**解决**：加入具体光效并加权重
```
❌ 好看的光
✅ (dramatic rim lighting:1.3), (volumetric light:1.2), side back cold white light
```

### 问题：氛围单薄
**解决**：添加环境元素
```
❌ 灰色背景
✅ dark gray to blue gradient background, cold mist rising from ice surface, volumetric fog
```

### 问题：主体不突出
**解决**：将主体放最前面，增加权重
```
❌ ice shattering, dark red smartphone, extreme low angle
✅ (dark red smartphone:1.5), (extreme low angle:1.3), ice shattering
```
