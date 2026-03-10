# API Reference: tensor2numpy.py

**Language**: Python

**Source**: `hivision/creator/tensor2numpy.py`

---

## Functions

### NTo_Tensor(array)

:param array: opencv/PIL读取的numpy矩阵
:return:返回一个形如 Tensor 的 numpy 矩阵
Example:
Inputs:array.shape = (512,512,3)
Outputs:output.shape = (3,512,512)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| array | None | - | - |

**Returns**: (none)



### NNormalize(array, mean = np.array([0.5, 0.5, 0.5]), std = np.array([0.5, 0.5, 0.5]), dtype = np.float32)

:param array: opencv/PIL读取的numpy矩阵
       mean: 归一化均值，np.array 格式
       std:  归一化标准差，np.array 格式
       dtype：输出的 numpy 数据格式，一般 onnx 需要 float32
:return:numpy 矩阵
Example:
Inputs:array 为 opencv/PIL 读取的一张图片
       mean=np.array([0.5,0.5,0.5])
       std=np.array([0.5,0.5,0.5])
       dtype=np.float32
Outputs:output 为归一化后的 numpy 矩阵

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| array | None | - | - |
| mean | None | np.array([0.5, 0.5, 0.5]) | - |
| std | None | np.array([0.5, 0.5, 0.5]) | - |
| dtype | None | np.float32 | - |

**Returns**: (none)



### NUnsqueeze(array, axis = 0)

:param array: opencv/PIL读取的numpy矩阵
       axis：要增加的维度
:return:numpy 矩阵
Example:
Inputs:array 为 opencv/PIL 读取的一张图片，array.shape 为 [512,512,3]
       axis=0
Outputs:output 为 array 在第 0 维增加一个维度，shape 转为 [1,512,512,3]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| array | None | - | - |
| axis | None | 0 | - |

**Returns**: (none)


