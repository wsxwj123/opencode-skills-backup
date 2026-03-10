# API Reference: context.py

**Language**: Python

**Source**: `hivision/creator/context.py`

---

## Classes

### Params

**Inherits from**: (none)

#### Methods

##### __init__(self, size: Tuple[int, int] = (413, 295), change_bg_only: bool = False, crop_only: bool = False, head_measure_ratio: float = 0.2, head_height_ratio: float = 0.45, head_top_range: float = (0.12, 0.1), face: Tuple[int, int, int, int] = None, whitening_strength: int = 0, brightness_strength: int = 0, contrast_strength: int = 0, sharpen_strength: int = 0, saturation_strength: int = 0, face_alignment: bool = False, horizontal_flip: bool = False)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| size | Tuple[int, int] | (413, 295) | - |
| change_bg_only | bool | False | - |
| crop_only | bool | False | - |
| head_measure_ratio | float | 0.2 | - |
| head_height_ratio | float | 0.45 | - |
| head_top_range | float | (0.12, 0.1) | - |
| face | Tuple[int, int, int, int] | None | - |
| whitening_strength | int | 0 | - |
| brightness_strength | int | 0 | - |
| contrast_strength | int | 0 | - |
| sharpen_strength | int | 0 | - |
| saturation_strength | int | 0 | - |
| face_alignment | bool | False | - |
| horizontal_flip | bool | False | - |


##### size(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### change_bg_only(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### head_measure_ratio(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### head_height_ratio(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### head_top_range(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### crop_only(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### face(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### whitening_strength(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### brightness_strength(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### contrast_strength(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### sharpen_strength(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### saturation_strength(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### face_alignment(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### horizontal_flip(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |




### Result

**Inherits from**: (none)

#### Methods

##### __init__(self, standard: np.ndarray, hd: np.ndarray, matting: np.ndarray, clothing_params: Optional[dict], typography_params: Optional[dict], face: Optional[Tuple[int, int, int, int, float]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| standard | np.ndarray | - | - |
| hd | np.ndarray | - | - |
| matting | np.ndarray | - | - |
| clothing_params | Optional[dict] | - | - |
| typography_params | Optional[dict] | - | - |
| face | Optional[Tuple[int, int, int, int, float]] | - | - |


##### __iter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |




### Context

**Inherits from**: (none)

#### Methods

##### __init__(self, params: Params)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| params | Params | - | - |



