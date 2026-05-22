# API Reference: photo_adjuster.py

**Language**: Python

**Source**: `hivision/creator/photo_adjuster.py`

---

## Functions

### adjust_photo(ctx: Context)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### IDphotos_cut(x1, y1, x2, y2, img)

在图片上进行滑动裁剪，输入输出为
输入：一张图片 img，和裁剪框信息 (x1,x2,y1,y2)
输出：裁剪好的图片，然后裁剪框超出了图像范围，那么将用 0 矩阵补位
------------------------------------
x:裁剪框左上的横坐标
y:裁剪框左上的纵坐标
x2:裁剪框右下的横坐标
y2:裁剪框右下的纵坐标
crop_size:裁剪框大小
img:裁剪图像（numpy.array）
output_path:裁剪图片的输出路径
------------------------------------

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| x1 | None | - | - |
| y1 | None | - | - |
| x2 | None | - | - |
| y2 | None | - | - |
| img | None | - | - |

**Returns**: (none)



### move(input_image)

裁剪主函数，输入一张 png 图像，该图像周围是透明的

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |

**Returns**: (none)



### standard_photo_resize(input_image: np.array, size)

input_image: 输入图像，即高清照
size: 标准照的尺寸

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | np.array | - | - |
| size | None | - | - |

**Returns**: (none)



### resize_image_by_min(input_image, esp = 600)

将图像缩放为最短边至少为 esp 的图像。
:param input_image: 输入图像（OpenCV 矩阵）
:param esp: 缩放后的最短边长
:return: 缩放后的图像，缩放倍率

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| esp | None | 600 | - |

**Returns**: (none)


