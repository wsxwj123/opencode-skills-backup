# API Reference: base_adjust.py

**Language**: Python

**Source**: `hivision/plugin/beauty/base_adjust.py`

---

## Functions

### adjust_brightness_contrast_sharpen_saturation(image, brightness_factor = 0, contrast_factor = 0, sharpen_strength = 0, saturation_factor = 0)

调整图像的亮度、对比度、锐度和饱和度。

参数:
image (numpy.ndarray): 输入的图像数组。
brightness_factor (float): 亮度调整因子。大于0增加亮度，小于0降低亮度。
contrast_factor (float): 对比度调整因子。大于0增加对比度，小于0降低对比度。
sharpen_strength (float): 锐化强度。
saturation_factor (float): 饱和度调整因子。大于0增加饱和度，小于0降低饱和度。

返回:
numpy.ndarray: 调整后的图像。

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| brightness_factor | None | 0 | - |
| contrast_factor | None | 0 | - |
| sharpen_strength | None | 0 | - |
| saturation_factor | None | 0 | - |

**Returns**: (none)



### adjust_saturation(image, saturation_factor)

调整图像的饱和度。

参数:
image (numpy.ndarray): 输入的图像数组。
saturation_factor (float): 饱和度调整因子。大于0增加饱和度，小于0降低饱和度。

返回:
numpy.ndarray: 调整后的图像。

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| saturation_factor | None | - | - |

**Returns**: (none)



### sharpen_image(image, strength = 0)

对图像进行锐化处理。

参数:
image (numpy.ndarray): 输入的图像数组。
strength (float): 锐化强度，范围建议为0-5。0表示不进行锐化。

返回:
numpy.ndarray: 锐化后的图像。

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| strength | None | 0 | - |

**Returns**: (none)



### base_adjustment(image, brightness, contrast, sharpen, saturation)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| brightness | None | - | - |
| contrast | None | - | - |
| sharpen | None | - | - |
| saturation | None | - | - |

**Returns**: (none)


