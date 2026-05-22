# API Reference: deploy_api.py

**Language**: Python

**Source**: `deploy_api.py`

---

## Functions

### idphoto_inference(input_image: UploadFile = File(None), input_image_base64: str = Form(None), height: int = Form(413), width: int = Form(295), human_matting_model: str = Form('modnet_photographic_portrait_matting'), face_detect_model: str = Form('mtcnn'), hd: bool = Form(True), dpi: int = Form(300), face_align: bool = Form(False), whitening_strength: int = Form(0), head_measure_ratio: float = Form(0.2), head_height_ratio: float = Form(0.45), top_distance_max: float = Form(0.12), top_distance_min: float = Form(0.1), brightness_strength: float = Form(0), contrast_strength: float = Form(0), sharpen_strength: float = Form(0), saturation_strength: float = Form(0))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| height | int | Form(413) | - |
| width | int | Form(295) | - |
| human_matting_model | str | Form('modnet_photographic_portrait_matting') | - |
| face_detect_model | str | Form('mtcnn') | - |
| hd | bool | Form(True) | - |
| dpi | int | Form(300) | - |
| face_align | bool | Form(False) | - |
| whitening_strength | int | Form(0) | - |
| head_measure_ratio | float | Form(0.2) | - |
| head_height_ratio | float | Form(0.45) | - |
| top_distance_max | float | Form(0.12) | - |
| top_distance_min | float | Form(0.1) | - |
| brightness_strength | float | Form(0) | - |
| contrast_strength | float | Form(0) | - |
| sharpen_strength | float | Form(0) | - |
| saturation_strength | float | Form(0) | - |

**Returns**: (none)



### human_matting_inference(input_image: UploadFile = File(None), input_image_base64: str = Form(None), human_matting_model: str = Form('hivision_modnet'), dpi: int = Form(300))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| human_matting_model | str | Form('hivision_modnet') | - |
| dpi | int | Form(300) | - |

**Returns**: (none)



### photo_add_background(input_image: UploadFile = File(None), input_image_base64: str = Form(None), color: str = Form('000000'), kb: int = Form(None), dpi: int = Form(300), render: int = Form(0))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| color | str | Form('000000') | - |
| kb | int | Form(None) | - |
| dpi | int | Form(300) | - |
| render | int | Form(0) | - |

**Returns**: (none)



### generate_layout_photos(input_image: UploadFile = File(None), input_image_base64: str = Form(None), height: int = Form(413), width: int = Form(295), kb: int = Form(None), dpi: int = Form(300))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| height | int | Form(413) | - |
| width | int | Form(295) | - |
| kb | int | Form(None) | - |
| dpi | int | Form(300) | - |

**Returns**: (none)



### watermark(input_image: UploadFile = File(None), input_image_base64: str = Form(None), text: str = Form('Hello'), size: int = 20, opacity: float = 0.5, angle: int = 30, color: str = '#000000', space: int = 25, kb: int = Form(None), dpi: int = Form(300))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| text | str | Form('Hello') | - |
| size | int | 20 | - |
| opacity | float | 0.5 | - |
| angle | int | 30 | - |
| color | str | '#000000' | - |
| space | int | 25 | - |
| kb | int | Form(None) | - |
| dpi | int | Form(300) | - |

**Returns**: (none)



### set_kb(input_image: UploadFile = File(None), input_image_base64: str = Form(None), dpi: int = Form(300), kb: int = Form(50))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| dpi | int | Form(300) | - |
| kb | int | Form(50) | - |

**Returns**: (none)



### idphoto_crop_inference(input_image: UploadFile = File(None), input_image_base64: str = Form(None), height: int = Form(413), width: int = Form(295), face_detect_model: str = Form('mtcnn'), hd: bool = Form(True), dpi: int = Form(300), head_measure_ratio: float = Form(0.2), head_height_ratio: float = Form(0.45), top_distance_max: float = Form(0.12), top_distance_min: float = Form(0.1))

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | UploadFile | File(None) | - |
| input_image_base64 | str | Form(None) | - |
| height | int | Form(413) | - |
| width | int | Form(295) | - |
| face_detect_model | str | Form('mtcnn') | - |
| hd | bool | Form(True) | - |
| dpi | int | Form(300) | - |
| head_measure_ratio | float | Form(0.2) | - |
| head_height_ratio | float | Form(0.45) | - |
| top_distance_max | float | Form(0.12) | - |
| top_distance_min | float | Form(0.1) | - |

**Returns**: (none)


