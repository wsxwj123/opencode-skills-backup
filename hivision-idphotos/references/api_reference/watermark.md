# API Reference: watermark.py

**Language**: Python

**Source**: `hivision/plugin/watermark.py`

---

## Classes

### WatermarkerStyles

水印样式

**Inherits from**: enum.Enum



### Watermarker

图片水印工具

**Inherits from**: object

#### Methods

##### __init__(self, input_image: Image.Image, text: str, style: WatermarkerStyles, angle = 30, color = '#8B8B1B', font_file = '青鸟华光简琥珀.ttf', opacity = 0.15, size = 50, space = 75, chars_per_line = 8, font_height_crop = 1.2)

_summary_

Parameters
----------
input_image : Image.Image
    PIL图片对象
text : str
    水印文字
style : WatermarkerStyles
    水印样式
angle : int, optional
    水印角度, by default 30
color : str, optional
    水印颜色, by default "#8B8B1B"
font_file : str, optional
    字体文件, by default "青鸟华光简琥珀.ttf"
font_height_crop : float, optional
    字体高度裁剪比例, by default 1.2
opacity : float, optional
    水印透明度, by default 0.15
size : int, optional
    字体大小, by default 50
space : int, optional
    水印间距, by default 75
chars_per_line : int, optional
    每行字符数, by default 8

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| input_image | Image.Image | - | - |
| text | str | - | - |
| style | WatermarkerStyles | - | - |
| angle | None | 30 | - |
| color | None | '#8B8B1B' | - |
| font_file | None | '青鸟华光简琥珀.ttf' | - |
| opacity | None | 0.15 | - |
| size | None | 50 | - |
| space | None | 75 | - |
| chars_per_line | None | 8 | - |
| font_height_crop | None | 1.2 | - |


##### set_image_opacity(image: Image, opacity: float)

**Decorators**: `@staticmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | Image | - | - |
| opacity | float | - | - |


##### crop_image_edge(image: Image)

**Decorators**: `@staticmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | Image | - | - |


##### _add_mark_striped(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### _add_mark_central(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### image(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### save(self, file_path: str, image_format: str = 'png')

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| file_path | str | - | - |
| image_format | str | 'png' | - |




## Functions

### watermark_image(image, text, style, angle, color, opacity, size, space)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| text | None | - | - |
| style | None | - | - |
| angle | None | - | - |
| color | None | - | - |
| opacity | None | - | - |
| size | None | - | - |
| space | None | - | - |

**Returns**: (none)


