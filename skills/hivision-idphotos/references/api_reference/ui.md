# API Reference: ui.py

**Language**: Python

**Source**: `demo/ui.py`

---

## Functions

### load_description(fp)

加载title.md文件作为Demo的顶部栏

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| fp | None | - | - |

**Returns**: (none)



### create_ui(processor: IDPhotoProcessor, root_dir: str, human_matting_models: list, face_detect_models: list, language: list)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| processor | IDPhotoProcessor | - | - |
| root_dir | str | - | - |
| human_matting_models | list | - | - |
| face_detect_models | list | - | - |
| language | list | - | - |

**Returns**: (none)



### change_language(language)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| language | None | - | - |

**Returns**: (none)



### change_visibility(option, lang, locales_key, custom_component)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| option | None | - | - |
| lang | None | - | - |
| locales_key | None | - | - |
| custom_component | None | - | - |

**Returns**: (none)



### change_color(colors, lang)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| colors | None | - | - |
| lang | None | - | - |

**Returns**: (none)



### change_size_mode(size_option_item, lang)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| size_option_item | None | - | - |
| lang | None | - | - |

**Returns**: (none)



### change_image_kb(image_kb_option, lang)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image_kb_option | None | - | - |
| lang | None | - | - |

**Returns**: (none)



### change_image_dpi(image_dpi_option, lang)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| image_dpi_option | None | - | - |
| lang | None | - | - |

**Returns**: (none)



### update_watermark_text_visibility(choice, language)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| choice | None | - | - |
| language | None | - | - |

**Returns**: (none)


