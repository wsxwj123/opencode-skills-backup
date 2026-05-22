# API Reference: rotation_adjust.py

**Language**: Python

**Source**: `hivision/creator/rotation_adjust.py`

---

## Functions

### rotate_bound(image: np.ndarray, angle: float, center = None)

旋转图像而不损失信息的函数

Args:
    image (np.ndarray): 输入图像，3通道numpy数组
    angle (float): 旋转角度（度）
    center (tuple, optional): 旋转中心坐标，默认为图像中心

Returns:
    tuple: 包含以下元素的元组：
        - rotated (np.ndarray): 旋转后的图像
        - cos (float): 旋转角度的余弦值
        - sin (float): 旋转角度的正弦值
        - dW (int): 宽度变化量
        - dH (int): 高度变化量

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | np.ndarray | - | - |
| angle | float | - | - |
| center | None | None | - |

**Returns**: (none)



### rotate_bound_4channels(image: np.ndarray, a: np.ndarray, angle: float, center = None)

旋转4通道图像的函数

这是rotate_bound函数的4通道版本，可以同时处理RGB图像和其对应的alpha通道。

Args:
    image (np.ndarray): 输入的3通道RGB图像
    a (np.ndarray): 输入图像的alpha通道
    angle (float): 旋转角度（度）
    center (tuple, optional): 旋转中心坐标，默认为图像中心

Returns:
    tuple: 包含以下元素的元组：
        - input_image (np.ndarray): 旋转后的3通道RGB图像
        - result_image (np.ndarray): 旋转后的4通道RGBA图像
        - cos (float): 旋转角度的余弦值
        - sin (float): 旋转角度的正弦值
        - dW (int): 宽度变化量
        - dH (int): 高度变化量

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | np.ndarray | - | - |
| a | np.ndarray | - | - |
| angle | float | - | - |
| center | None | None | - |

**Returns**: (none)


