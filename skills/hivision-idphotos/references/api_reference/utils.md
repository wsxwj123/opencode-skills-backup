# API Reference: utils.py

**Language**: Python

**Source**: `hivision/utils.py`

---

## Functions

### save_image_dpi_to_bytes(image: np.ndarray, output_image_path: str = None, dpi: int = 300)

设置图像的DPI（每英寸点数）并返回字节流

:param image: numpy.ndarray, 输入的图像数组
:param output_image_path: Path to save the resized image. 保存调整大小后的图像的路径。
:param dpi: int, 要设置的DPI值，默认为300

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | np.ndarray | - | - |
| output_image_path | str | None | - |
| dpi | int | 300 | - |

**Returns**: (none)



### resize_image_to_kb(input_image: np.ndarray, output_image_path: str = None, target_size_kb: int = 100, dpi: int = 300)

Resize an image to a target size in KB.
将图像调整大小至目标文件大小（KB）。

:param input_image_path: Path to the input image. 输入图像的路径。
:param output_image_path: Path to save the resized image. 保存调整大小后的图像的路径。
:param target_size_kb: Target size in KB. 目标文件大小（KB）。

Example:
resize_image_to_kb('input_image.jpg', 'output_image.jpg', 50)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | np.ndarray | - | - |
| output_image_path | str | None | - |
| target_size_kb | int | 100 | - |
| dpi | int | 300 | - |

**Returns**: (none)



### resize_image_to_kb_base64(input_image, target_size_kb, mode = 'exact')

Resize an image to a target size in KB and return it as a base64 encoded string.
将图像调整大小至目标文件大小（KB）并返回base64编码的字符串。

:param input_image: Input image as a NumPy array or PIL Image. 输入图像，可以是NumPy数组或PIL图像。
:param target_size_kb: Target size in KB. 目标文件大小（KB）。
:param mode: Mode of resizing ('exact', 'max', 'min'). 模式：'exact'（精确大小）、'max'（不大于）、'min'（不小于）。

:return: Base64 encoded string of the resized image. 调整大小后的图像的base64编码字符串。

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| target_size_kb | None | - | - |
| mode | None | 'exact' | - |

**Returns**: (none)



### numpy_2_base64(img: np.ndarray) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| img | np.ndarray | - | - |

**Returns**: `str`



### base64_2_numpy(base64_image: str) → np.ndarray

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| base64_image | str | - | - |

**Returns**: `np.ndarray`



### bytes_2_base64(img_byte_arr: bytes) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| img_byte_arr | bytes | - | - |

**Returns**: `str`



### save_numpy_image(numpy_img, file_path)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| numpy_img | None | - | - |
| file_path | None | - | - |

**Returns**: (none)



### numpy_to_bytes(numpy_img)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| numpy_img | None | - | - |

**Returns**: (none)



### hex_to_rgb(value)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| value | None | - | - |

**Returns**: (none)



### generate_gradient(start_color, width, height, mode = 'updown')

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| start_color | None | - | - |
| width | None | - | - |
| height | None | - | - |
| mode | None | 'updown' | - |

**Returns**: (none)



### add_background(input_image, bgr = (0, 0, 0), mode = 'pure_color')

本函数的功能为为透明图像加上背景。
:param input_image: numpy.array(4 channels), 透明图像
:param bgr: tuple, 合成纯色底时的 BGR 值
:param new_background: numpy.array(3 channels)，合成自定义图像底时的背景图
:return: output: 合成好的输出图像

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| bgr | None | (0, 0, 0) | - |
| mode | None | 'pure_color' | - |

**Returns**: (none)



### add_background_with_image(input_image: np.ndarray, background_image: np.ndarray) → np.ndarray

本函数的功能为为透明图像加上背景。
:param input_image: numpy.array(4 channels), 透明图像
:param background_image: numpy.array(3 channels), 背景图像
:return: output: 合成好的输出图像

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | np.ndarray | - | - |
| background_image | np.ndarray | - | - |

**Returns**: `np.ndarray`



### add_watermark(image, text, size = 50, opacity = 0.5, angle = 45, color = '#8B8B1B', space = 75)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| text | None | - | - |
| size | None | 50 | - |
| opacity | None | 0.5 | - |
| angle | None | 45 | - |
| color | None | '#8B8B1B' | - |
| space | None | 75 | - |

**Returns**: (none)


