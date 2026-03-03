# API Reference: thin_face.py

**Language**: Python

**Source**: `hivision/plugin/beauty/thin_face.py`

---

## Classes

### TranslationWarp

本类包含瘦脸算法，由于瘦脸算法包含了很多个版本，所以以类的方式呈现
前两个算法没什么好讲的，网上资料很多
第三个采用numpy内部的自定义函数处理，在处理速度上有一些提升
最后采用cv2.map算法，处理速度大幅度提升

**Inherits from**: object

#### Methods

##### localTranslationWarp(srcImg, startX, startY, endX, endY, radius)

**Decorators**: `@staticmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| srcImg | None | - | - |
| startX | None | - | - |
| startY | None | - | - |
| endX | None | - | - |
| endY | None | - | - |
| radius | None | - | - |


##### localTranslationWarpLimitFor(srcImg, startP: np.matrix, endP: np.matrix, radius: float)

**Decorators**: `@staticmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| srcImg | None | - | - |
| startP | np.matrix | - | - |
| endP | np.matrix | - | - |
| radius | float | - | - |


##### localTranslationWarpFastWithStrength(srcImg, startP: np.matrix, endP: np.matrix, radius, strength: float = 100.0)

采用opencv内置函数
Args:
    srcImg: 源图像
    startP: 起点位置
    endP: 终点位置
    radius: 处理半径
    strength: 瘦脸强度，一般取100以上

Returns:

**Decorators**: `@staticmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| srcImg | None | - | - |
| startP | np.matrix | - | - |
| endP | np.matrix | - | - |
| radius | None | - | - |
| strength | float | 100.0 | - |




## Functions

### thinFace(src, landmark, place: int = 0, strength = 30.0)

瘦脸程序接口，输入人脸关键点信息和强度，即可实现瘦脸
注意处理四通道图像
Args:
    src: 原图
    landmark: 关键点信息
    place: 选择瘦脸区域，为0-4之间的值
    strength: 瘦脸强度，输入值在0-10之间，如果小于或者等于0，则不瘦脸

Returns:
    瘦脸后的图像

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| src | None | - | - |
| landmark | None | - | - |
| place | int | 0 | - |
| strength | None | 30.0 | - |

**Returns**: (none)



### BilinearInsert(src, ux, uy)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| src | None | - | - |
| ux | None | - | - |
| uy | None | - | - |

**Returns**: (none)



### BilinearInsert(src, ux, uy)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| src | None | - | - |
| ux | None | - | - |
| uy | None | - | - |

**Returns**: (none)


