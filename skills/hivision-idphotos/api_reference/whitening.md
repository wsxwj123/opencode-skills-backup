# API Reference: whitening.py

**Language**: Python

**Source**: `hivision/plugin/beauty/whitening.py`

---

## Classes

### LutWhite

**Inherits from**: (none)

#### Methods

##### __init__(self, lut_image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| lut_image | None | - | - |


##### _create_lut(self, lut_image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| lut_image | None | - | - |


##### apply(self, src)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| src | None | - | - |




### MakeWhiter

**Inherits from**: (none)

#### Methods

##### __init__(self, lut_image)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| lut_image | None | - | - |


##### run(self, src: np.ndarray, strength: int) → np.ndarray

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| src | np.ndarray | - | - |
| strength | int | - | - |

**Returns**: `np.ndarray`




## Functions

### make_whitening(image, strength)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| strength | None | - | - |

**Returns**: (none)



### make_whitening_png(image, strength)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image | None | - | - |
| strength | None | - | - |

**Returns**: (none)


