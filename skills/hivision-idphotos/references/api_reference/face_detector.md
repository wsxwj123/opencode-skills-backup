# API Reference: face_detector.py

**Language**: Python

**Source**: `hivision/creator/face_detector.py`

---

## Functions

### detect_face_mtcnn(ctx: Context, scale: int = 2)

基于MTCNN模型的人脸检测处理器，只进行人脸数量的检测
:param ctx: 上下文，此时已获取到原始图和抠图结果，但是我们只需要原始图
:param scale: 最大边长缩放比例，原图:缩放图 = 1:scale
:raise FaceError: 人脸检测错误，多个人脸或者没有人脸

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |
| scale | int | 2 | - |

**Returns**: (none)



### detect_face_face_plusplus(ctx: Context)

基于Face++ API接口的人脸检测处理器，只进行人脸数量的检测
:param ctx: 上下文，此时已获取到原始图和抠图结果，但是我们只需要原始图
:param scale: 最大边长缩放比例，原图:缩放图 = 1:scale
:raise FaceError: 人脸检测错误，多个人脸或者没有人脸

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### detect_face_retinaface(ctx: Context)

基于RetinaFace模型的人脸检测处理器，只进行人脸数量的检测
:param ctx: 上下文，此时已获取到原始图和抠图结果，但是我们只需要原始图
:raise FaceError: 人脸检测错误，多个人脸或者没有人脸

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)


