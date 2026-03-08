---
name: moebius-style-art-prompt
description: Use when users ask to generate, expand, or rewrite image prompts into Moebius-style/清线描 fantasy concept art with strict bilingual plaintext blocks, fixed section structure, camera-angle vocabulary constraints, and mandatory keyword injection.
---

# mobieus-style-art-prompt

## Overview
把用户的场景描述转成高质量绘图提示词，输出中英双语版本，强调“柔和清线描 + 饱满构图 + 秩序化纯色块”的统一视觉语言。

## When to Use
在以下场景直接使用本 skill：
- 用户要“生成提示词 / 扩写提示词 / 风格改写提示词”
- 用户明确提到 Moebius、清线描、RPG 概念艺术、平涂块面
- 用户要求镜头视角规范化、构图约束、颜色限制
- 用户要求中英双语提示词并限制输出格式

## Input Handling
读取用户输入时，先提取 5 个要素：
1. 场景主体（人物/建筑/遗迹/生物）
2. 场景环境（森林/城镇/地下城/天穹等）
3. 叙事气质（史诗、神秘、宁静、紧张）
4. 视角需求（若未给出则自动推断）
5. 构图密度（默认高密度、少留白）

## Style Directives
### 1) 艺术风格与线条
- 必须包含：Moebius style + Soft Ligne Claire
- 使用适中且柔和轮廓线（medium-weight, delicate outlines）
- 线条仅勾勒外轮廓与主要结构
- 禁止密集排线（hatching）表现质感
- 体积主要由色块关系表达
- 避免过度锐化与矢量图标感

### 2) 构图与空间
- 强制高视平线（High Horizon Line）
- 地面景观占画面 80%-90%
- 采用饱满构图（Dense / Frame-filling）
- 显著减少负空间，尤其避免大面积单色天空
- 背景必须为可识别景物，不得是空洞虚化背景

### 3) 色彩与上色
- 严格平涂（Strict flat coloring）
- 限定背景主色 3-4 种大面积纯色
- 点缀色克制且统一
- 同类元素保持同一纯色编码

### 4) 题材氛围
- retro 2D fantasy RPG art
- 史诗感由“景物复杂度与层次”体现，不靠空旷留白

## Camera Angle Reference (must select from this list)
### 垂直角度
- top-down view, bird's-eye view, directly overhead
- high angle shot, 45-degree overhead view, three-quarter overhead view
- eye-level shot, straight-on view
- low angle shot, worm's-eye view, looking up
- extreme low angle, ant's-eye view

### 水平方位
- front view, facing the camera
- rear view, back view
- side view, profile view
- over-the-shoulder shot

### 特殊视角
- first-person POV, subjective camera
- Dutch angle, tilted frame
- fisheye lens, barrel distortion

### 焦距与空间感
- ultra wide-angle lens, exaggerated perspective
- standard lens, natural perspective
- telephoto lens, compressed perspective

### 万能公式
- camera positioned at [anchor], looking [direction] at [target]

### 透视增强
- dramatic foreshortening
- strong depth, vanishing point perspective

## Output Format (exactly six sections)
按以下顺序组织提示词内容（中文与英文都遵循）：
1. 艺术风格关键词
2. 镜头角度
3. 构图技法
4. 环境/背景描述
5. 主体描述
6. 颜色/上色限制关键词

### 标题一致性（新增）
- 中文 `plaintext` 代码块中，六段标题必须逐字使用以下文本（不得加编号前缀如 `1.`、`2)`）：
  - 艺术风格关键词
  - 镜头角度
  - 构图技法
  - 环境/背景描述
  - 主体描述
  - 颜色/上色限制关键词
- 英文 `plaintext` 代码块中，六段标题必须逐字使用以下文本（不得加编号前缀）：
  - Art Style Keywords
  - Camera Angle
  - Composition Techniques
  - Environment/Background Description
  - Subject Description
  - Color/Rendering Constraint Keywords

## Hard Constraints
- 最终只输出提示词，不输出解释、推理、参数
- 必须输出两个 `plaintext` 代码块：第一个中文，第二个英文
- 镜头角度段落必须从 Camera Angle Reference 中选词
- 必须包含以下 Mandatory Keywords（英文原样保留）
- 中文代码块默认以中文描述为主；英文仅允许用于：
  - Mandatory Keywords 原文
  - Camera Angle Reference 选词原文
  - 必要的风格术语（如 Moebius style, Soft Ligne Claire）
  其余叙述内容应保持中文，不写英文解释句

## Mandatory Keywords
Moebius style, Soft Ligne Claire, delicate outlines, full color illustration, vibrant colors, cel shading, strict flat coloring, NO gradients, highly ordered color blocks, retro 2D fantasy RPG art, detailed

## Generation Procedure
1. 解析用户输入并补齐缺失的构图信息
2. 从 Camera Angle Reference 选择最匹配的镜头词
3. 组装六段结构（先中文再英文）
4. 在中英文提示词中注入 Mandatory Keywords
5. 检查禁用项（参数、额外解释、无关符号）

## Final Output Template
```plaintext
[中文提示词：按六段结构组织，段间空一行]
```

```plaintext
[English prompt: same six-section structure with blank lines between sections]
```
