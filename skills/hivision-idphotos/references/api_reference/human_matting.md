# API Reference: human_matting.py

**Language**: Python

**Source**: `hivision/creator/human_matting.py`

---

## Functions

### load_onnx_model(checkpoint_path, set_cpu = False)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| checkpoint_path | None | - | - |
| set_cpu | None | False | - |

**Returns**: (none)



### extract_human(ctx: Context)

人像抠图
:param ctx: 上下文

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### extract_human_modnet_photographic_portrait_matting(ctx: Context)

人像抠图
:param ctx: 上下文

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### extract_human_mnn_modnet(ctx: Context)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### extract_human_rmbg(ctx: Context)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### extract_human_birefnet_lite(ctx: Context)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| ctx | Context | - | - |

**Returns**: (none)



### hollow_out_fix(src: np.ndarray) → np.ndarray

修补抠图区域，作为抠图模型精度不够的补充
:param src:
:return:

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| src | np.ndarray | - | - |

**Returns**: `np.ndarray`



### image2bgr(input_image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |

**Returns**: (none)



### read_modnet_image(input_image, ref_size = 512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| ref_size | None | 512 | - |

**Returns**: (none)



### get_modnet_matting(input_image, checkpoint_path, ref_size = 512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| checkpoint_path | None | - | - |
| ref_size | None | 512 | - |

**Returns**: (none)



### get_modnet_matting_photographic_portrait_matting(input_image, checkpoint_path, ref_size = 512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| checkpoint_path | None | - | - |
| ref_size | None | 512 | - |

**Returns**: (none)



### get_rmbg_matting(input_image: np.ndarray, checkpoint_path, ref_size = 1024)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | np.ndarray | - | - |
| checkpoint_path | None | - | - |
| ref_size | None | 1024 | - |

**Returns**: (none)



### get_mnn_modnet_matting(input_image, checkpoint_path, ref_size = 512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| checkpoint_path | None | - | - |
| ref_size | None | 512 | - |

**Returns**: (none)



### get_birefnet_portrait_matting(input_image, checkpoint_path, ref_size = 512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_image | None | - | - |
| checkpoint_path | None | - | - |
| ref_size | None | 512 | - |

**Returns**: (none)



### resize_rmbg_image(image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |

**Returns**: (none)



### transform_image(image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |

**Returns**: (none)


