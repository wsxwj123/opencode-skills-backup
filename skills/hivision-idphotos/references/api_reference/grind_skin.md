# API Reference: grind_skin.py

**Language**: Python

**Source**: `hivision/plugin/beauty/grind_skin.py`

---

## Functions

### annotate_image(image, grind_degree, detail_degree, strength)

Annotates the image with parameters in the lower-left corner.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| grind_degree | None | - | - |
| detail_degree | None | - | - |
| strength | None | - | - |

**Returns**: (none)



### grindSkin(src, grindDegree: int = 3, detailDegree: int = 1, strength: int = 9)

Dest =(Src * (100 - Opacity) + (Src + 2 * GaussBlur(EPFFilter(Src) - Src)) * Opacity) / 100
人像磨皮方案
Args:
    src: 原图
    grindDegree: 磨皮程度调节参数
    detailDegree: 细节程度调节参数
    strength: 融合程度，作为磨皮强度（0 - 10）

Returns:
    磨皮后的图像

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| src | None | - | - |
| grindDegree | int | 3 | - |
| detailDegree | int | 1 | - |
| strength | int | 9 | - |

**Returns**: (none)



### process_image(input_img, grind_degree, detail_degree, strength)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_img | None | - | - |
| grind_degree | None | - | - |
| detail_degree | None | - | - |
| strength | None | - | - |

**Returns**: (none)


