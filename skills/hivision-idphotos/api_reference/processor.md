# API Reference: processor.py

**Language**: Python

**Source**: `demo/processor.py`

---

## Classes

### IDPhotoProcessor

**Inherits from**: (none)

#### Methods

##### process(self, input_image, mode_option, size_list_option, color_option, render_option, image_kb_options, custom_color_R, custom_color_G, custom_color_B, custom_color_hex_value, custom_size_height, custom_size_width, custom_size_height_mm, custom_size_width_mm, custom_image_kb, language, matting_model_option, watermark_option, watermark_text, watermark_text_color, watermark_text_size, watermark_text_opacity, watermark_text_angle, watermark_text_space, face_detect_option, head_measure_ratio = 0.2, top_distance_max = 0.12, whitening_strength = 0, image_dpi_option = False, custom_image_dpi = None, brightness_strength = 0, contrast_strength = 0, sharpen_strength = 0, saturation_strength = 0, plugin_option = [], print_switch = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| input_image | None | - | - |
| mode_option | None | - | - |
| size_list_option | None | - | - |
| color_option | None | - | - |
| render_option | None | - | - |
| image_kb_options | None | - | - |
| custom_color_R | None | - | - |
| custom_color_G | None | - | - |
| custom_color_B | None | - | - |
| custom_color_hex_value | None | - | - |
| custom_size_height | None | - | - |
| custom_size_width | None | - | - |
| custom_size_height_mm | None | - | - |
| custom_size_width_mm | None | - | - |
| custom_image_kb | None | - | - |
| language | None | - | - |
| matting_model_option | None | - | - |
| watermark_option | None | - | - |
| watermark_text | None | - | - |
| watermark_text_color | None | - | - |
| watermark_text_size | None | - | - |
| watermark_text_opacity | None | - | - |
| watermark_text_angle | None | - | - |
| watermark_text_space | None | - | - |
| face_detect_option | None | - | - |
| head_measure_ratio | None | 0.2 | - |
| top_distance_max | None | 0.12 | - |
| whitening_strength | None | 0 | - |
| image_dpi_option | None | False | - |
| custom_image_dpi | None | None | - |
| brightness_strength | None | 0 | - |
| contrast_strength | None | 0 | - |
| sharpen_strength | None | 0 | - |
| saturation_strength | None | 0 | - |
| plugin_option | None | [] | - |
| print_switch | None | None | - |


##### _initialize_idphoto_json(self, mode_option, color_option, render_option, image_kb_options, layout_photo_crop_line_option, jpeg_format_option, print_switch)

初始化idphoto_json字典

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| mode_option | None | - | - |
| color_option | None | - | - |
| render_option | None | - | - |
| image_kb_options | None | - | - |
| layout_photo_crop_line_option | None | - | - |
| jpeg_format_option | None | - | - |
| print_switch | None | - | - |


##### _process_size_mode(self, idphoto_json, language, size_list_option, custom_size_height, custom_size_width, custom_size_height_mm, custom_size_width_mm)

处理尺寸模式

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| idphoto_json | None | - | - |
| language | None | - | - |
| size_list_option | None | - | - |
| custom_size_height | None | - | - |
| custom_size_width | None | - | - |
| custom_size_height_mm | None | - | - |
| custom_size_width_mm | None | - | - |


##### _process_color_mode(self, idphoto_json, language, color_option, custom_color_R, custom_color_G, custom_color_B, custom_color_hex_value)

处理颜色模式

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| idphoto_json | None | - | - |
| language | None | - | - |
| color_option | None | - | - |
| custom_color_R | None | - | - |
| custom_color_G | None | - | - |
| custom_color_B | None | - | - |
| custom_color_hex_value | None | - | - |


##### _generate_id_photo(self, creator: IDCreator, input_image, idphoto_json, language, head_measure_ratio, top_distance_max, top_distance_min, whitening_strength, brightness_strength, contrast_strength, sharpen_strength, saturation_strength, face_alignment_option, horizontal_flip_option)

生成证件照

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| creator | IDCreator | - | - |
| input_image | None | - | - |
| idphoto_json | None | - | - |
| language | None | - | - |
| head_measure_ratio | None | - | - |
| top_distance_max | None | - | - |
| top_distance_min | None | - | - |
| whitening_strength | None | - | - |
| brightness_strength | None | - | - |
| contrast_strength | None | - | - |
| sharpen_strength | None | - | - |
| saturation_strength | None | - | - |
| face_alignment_option | None | - | - |
| horizontal_flip_option | None | - | - |


##### _handle_photo_generation_error(self, language)

处理照片生成错误

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| language | None | - | - |


##### _process_generated_photo(self, result, idphoto_json, language, watermark_option, watermark_text, watermark_text_size, watermark_text_opacity, watermark_text_angle, watermark_text_space, watermark_text_color)

处理生成的照片

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| result | None | - | - |
| idphoto_json | None | - | - |
| language | None | - | - |
| watermark_option | None | - | - |
| watermark_text | None | - | - |
| watermark_text_size | None | - | - |
| watermark_text_opacity | None | - | - |
| watermark_text_angle | None | - | - |
| watermark_text_space | None | - | - |
| watermark_text_color | None | - | - |


##### _render_background(self, result_image_standard, result_image_hd, idphoto_json, language)

渲染背景

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| result_image_standard | None | - | - |
| result_image_hd | None | - | - |
| idphoto_json | None | - | - |
| language | None | - | - |


##### _generate_image_layout(self, idphoto_json, result_image_standard, language)

生成排版照片

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| idphoto_json | None | - | - |
| result_image_standard | None | - | - |
| language | None | - | - |


##### _generate_image_template(self, idphoto_json, result_image_hd, language)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| idphoto_json | None | - | - |
| result_image_hd | None | - | - |
| language | None | - | - |


##### _add_watermark(self, result_image_standard, result_image_hd, watermark_text, watermark_text_size, watermark_text_opacity, watermark_text_angle, watermark_text_space, watermark_text_color)

添加水印

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| result_image_standard | None | - | - |
| result_image_hd | None | - | - |
| watermark_text | None | - | - |
| watermark_text_size | None | - | - |
| watermark_text_opacity | None | - | - |
| watermark_text_angle | None | - | - |
| watermark_text_space | None | - | - |
| watermark_text_color | None | - | - |


##### _save_image(self, result_image_standard, result_image_hd, result_image_layout, idphoto_json, format = 'png')

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| result_image_standard | None | - | - |
| result_image_hd | None | - | - |
| result_image_layout | None | - | - |
| idphoto_json | None | - | - |
| format | None | 'png' | - |


##### _create_response(self, result_image_standard, result_image_hd, result_image_standard_png, result_image_hd_png, result_layout_image_gr, result_image_template_gr, result_image_template_accordion_gr)

创建响应

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| result_image_standard | None | - | - |
| result_image_hd | None | - | - |
| result_image_standard_png | None | - | - |
| result_image_hd_png | None | - | - |
| result_layout_image_gr | None | - | - |
| result_image_template_gr | None | - | - |
| result_image_template_accordion_gr | None | - | - |


##### _create_error_response(self, language)

创建错误响应

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| language | None | - | - |



