# API Reference: beauty_tools.py

**Language**: Python

**Source**: `hivision/plugin/beauty/beauty_tools.py`

---

## Functions

### BeautyTools(input_image: np.ndarray, landmark, thinStrength: int, thinPlace: int, grindStrength: int, whiterStrength: int) → np.ndarray

美颜工具的接口函数，用于实现美颜效果
Args:
    input_image: 输入的图像
    landmark: 瘦脸需要的人脸关键点信息，为fd68返回的第二个参数
    thinStrength: 瘦脸强度，为0-10（如果更高其实也没什么问题），当强度为0或者更低时，则不瘦脸
    thinPlace: 选择瘦脸区域，为0-2之间的值，越大瘦脸的点越靠下
    grindStrength: 磨皮强度，为0-10（如果更高其实也没什么问题），当强度为0或者更低时，则不磨皮
    whiterStrength: 美白强度，为0-10（如果更高其实也没什么问题），当强度为0或者更低时，则不美白
Returns:
    output_image 输出图像

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | np.ndarray | - | - |
| landmark | None | - | - |
| thinStrength | int | - | - |
| thinPlace | int | - | - |
| grindStrength | int | - | - |
| whiterStrength | int | - | - |

**Returns**: `np.ndarray`


