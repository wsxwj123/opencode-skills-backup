# API Reference: error.py

**Language**: Python

**Source**: `hivision/error.py`

---

## Classes

### FaceError

**Inherits from**: Exception

#### Methods

##### __init__(self, err, face_num)

证件照人脸错误，此时人脸检测失败，可能是没有检测到人脸或者检测到多个人脸
Args:
    err: 错误描述
    face_num: 告诉此时识别到的人像个数

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| err | None | - | - |
| face_num | None | - | - |




### APIError

**Inherits from**: Exception

#### Methods

##### __init__(self, err, status_code)

API错误
Args:
    err: 错误描述
    status_code: 告诉此时的错误状态码

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| err | None | - | - |
| status_code | None | - | - |



