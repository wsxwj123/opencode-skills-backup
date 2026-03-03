# API Reference: inference.py

**Language**: Python

**Source**: `hivision/creator/retinaface/inference.py`

---

## Functions

### py_cpu_nms(dets, thresh)

Pure Python NMS baseline.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| dets | None | - | - |
| thresh | None | - | - |

**Returns**: (none)



### load_onnx_model(checkpoint_path, set_cpu = False)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| checkpoint_path | None | - | - |
| set_cpu | None | False | - |

**Returns**: (none)



### retinaface_detect_faces(image, model_path: str, sess = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| model_path | str | - | - |
| sess | None | None | - |

**Returns**: (none)


