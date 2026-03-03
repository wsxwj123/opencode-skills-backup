# API Reference: __init__.py

**Language**: Python

**Source**: `hivision/creator/__init__.py`

---

## Classes

### IDCreator

证件照创建类，包含完整的证件照流程

**Inherits from**: (none)

#### Methods

##### __init__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __call__(self, image: np.ndarray, size: Tuple[int, int] = (413, 295), change_bg_only: bool = False, crop_only: bool = False, head_measure_ratio: float = 0.2, head_height_ratio: float = 0.45, head_top_range: float = (0.12, 0.1), face: Tuple[int, int, int, int] = None, whitening_strength: int = 0, brightness_strength: int = 0, contrast_strength: int = 0, sharpen_strength: int = 0, saturation_strength: int = 0, face_alignment: bool = False, horizontal_flip: bool = False) → Result

证件照处理函数
:param image: 输入图像
:param change_bg_only: 是否只需要抠图
:param crop_only: 是否只需要裁剪
:param size: 输出的图像大小（h,w)
:param head_measure_ratio: 人脸面积与全图面积的期望比值
:param head_height_ratio: 人脸中心处在全图高度的比例期望值
:param head_top_range: 头距离顶部的比例（max,min)
:param face: 人脸坐标
:param whitening_strength: 美白强度
:param brightness_strength: 亮度强度
:param contrast_strength: 对比度强度
:param sharpen_strength: 锐化强度
:param face_alignment: 是否需要人脸矫正
:param horizontal_flip: 是否需要水平翻转

:return: 返回处理后的证件照和一系列参数

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| image | np.ndarray | - | - |
| size | Tuple[int, int] | (413, 295) | - |
| change_bg_only | bool | False | - |
| crop_only | bool | False | - |
| head_measure_ratio | float | 0.2 | - |
| head_height_ratio | float | 0.45 | - |
| head_top_range | float | (0.12, 0.1) | - |
| face | Tuple[int, int, int, int] | None | - |
| whitening_strength | int | 0 | - |
| brightness_strength | int | 0 | - |
| contrast_strength | int | 0 | - |
| sharpen_strength | int | 0 | - |
| saturation_strength | int | 0 | - |
| face_alignment | bool | False | - |
| horizontal_flip | bool | False | - |

**Returns**: `Result`



