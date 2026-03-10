# API Reference: move_image.py

**Language**: Python

**Source**: `hivision/creator/move_image.py`

---

## Functions

### merge(boxes)

生成的边框可能不止只有一个，需要将边框合并

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| boxes | None | - | - |

**Returns**: (none)



### get_box(png_img)

获取矩形边框最终返回一个元组 (x,y,h,w)，分别对应矩形左上角的坐标和矩形的高和宽

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| png_img | None | - | - |

**Returns**: (none)



### get_box_2(png_img)

不用 opencv 内置算法生成矩形了，改用自己的算法（for 循环）

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| png_img | None | - | - |

**Returns**: (none)



### move(input_image)

裁剪主函数，输入一张 png 图像，该图像周围是透明的

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |

**Returns**: (none)



### main()

**Returns**: (none)


