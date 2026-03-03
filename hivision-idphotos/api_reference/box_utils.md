# API Reference: box_utils.py

**Language**: Python

**Source**: `hivision/creator/retinaface/box_utils.py`

---

## Functions

### decode(loc, priors, variances)

Decode locations from predictions using priors to undo
the encoding we did for offset regression at train time.
Args:
    loc (tensor): location predictions for loc layers,
        Shape: [num_priors,4]
    priors (tensor): Prior boxes in center-offset form.
        Shape: [num_priors,4].
    variances: (list[float]) Variances of priorboxes
Return:
    decoded bounding box predictions

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| loc | None | - | - |
| priors | None | - | - |
| variances | None | - | - |

**Returns**: (none)



### decode_landm(pre, priors, variances)

Decode landm from predictions using priors to undo
the encoding we did for offset regression at train time.
Args:
    pre (tensor): landm predictions for loc layers,
        Shape: [num_priors,10]
    priors (tensor): Prior boxes in center-offset form.
        Shape: [num_priors,4].
    variances: (list[float]) Variances of priorboxes
Return:
    decoded landm predictions

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| pre | None | - | - |
| priors | None | - | - |
| variances | None | - | - |

**Returns**: (none)


