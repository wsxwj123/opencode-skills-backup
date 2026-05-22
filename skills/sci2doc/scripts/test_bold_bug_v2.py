import re

# 复制自 markdown_to_docx.py 的新逻辑
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*|__(.+?)__')
_SIGNIFICANCE_PROTECT_RE = re.compile(r'(\*{1,4})(\s*)([pP][<>≤≥=])')

def strip_bold_markers(text):
    placeholders = []

    def protect(m):
        token = f"§SIG{len(placeholders)}§"
        placeholders.append(m.group(0))
        return token

    # 1. 保护
    temp_text = _SIGNIFICANCE_PROTECT_RE.sub(protect, text)

    # 2. 去粗体
    stripped_text = _BOLD_RE.sub(lambda m: m.group(1) or m.group(2), temp_text)

    # 3. 还原
    for i, original in enumerate(placeholders):
        stripped_text = stripped_text.replace(f"§SIG{i}§", original)

    return stripped_text

# 测试用例
test_cases = [
    ("这是**粗体**文字", "这是粗体文字"),
    ("差异显著(*p<0.05)", "差异显著(*p<0.05)"),
    ("极显著(**P<0.01)", "极显著(**P<0.01)"),
    ("高度显著(***P<0.001)", "高度显著(***P<0.001)"),
    ("两组对比：A组(**P<0.01)且B组(**P<0.01)", "两组对比：A组(**P<0.01)且B组(**P<0.01)"),  # 关键修复点
    ("混合测试：这是**加粗**，而这是显著性**P<0.01", "混合测试：这是加粗，而这是显著性**P<0.01"),
    ("空格测试：* P<0.05", "空格测试：* P<0.05") # 关键修复点
]

print("--- 最终修复验证 ---")
all_passed = True
for raw, expected in test_cases:
    result = strip_bold_markers(raw)
    if result == expected:
        print(f"✅ {raw}")
    else:
        print(f"❌ {raw}\n   Exp: {expected}\n   Got: {result}")
        all_passed = False

if all_passed:
    print("\n🎉 所有测试通过！")
else:
    print("\n💥 仍有测试失败！")
