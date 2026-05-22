import re

# 当前的逻辑
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*|__(.+?)__')

def current_strip_bold(text):
    return _BOLD_RE.sub(lambda m: m.group(1) or m.group(2), text)

# 新的建议逻辑：保护-处理-还原
# 1. 保护显著性标记：匹配 * 或 ** 或 *** 后紧跟 p/P 的情况
# 注意：显著性通常是 *p, **p, ***p，但也可能是 * p (带空格)
_SIGNIFICANCE_PROTECT_RE = re.compile(r'(\*{1,4})\s*([pP][<>≤≥=])')

def robust_strip_bold(text):
    # 1. 保护：将显著性星号替换为占位符，例如 <STAR>
    # group(1) 是星号，group(2) 是 p<0.05 部分
    # 我们把星号替换为特殊的占位符，比如 §STAR§
    # 只有当星号后面紧跟 P/p 和比较符时才保护
    
    placeholders = []
    
    def protect(m):
        stars = m.group(1)
        rest = m.group(2)
        # 生成唯一占位符
        token = f"§SIG{len(placeholders)}§"
        placeholders.append(stars) 
        return token + rest

    # 保护步骤
    temp_text = _SIGNIFICANCE_PROTECT_RE.sub(protect, text)
    
    # 2. 去粗体
    # 现在的 temp_text 里已经没有显著性星号了，剩下的 ** 肯定是 Markdown 加粗
    stripped_text = _BOLD_RE.sub(lambda m: m.group(1) or m.group(2), temp_text)
    
    # 3. 还原
    for i, stars in enumerate(placeholders):
        stripped_text = stripped_text.replace(f"§SIG{i}§", stars)
        
    return stripped_text

# 测试用例
test_cases = [
    ("这是**粗体**文字", "这是粗体文字"),
    ("差异显著(*p<0.05)", "差异显著(*p<0.05)"),
    ("极显著(**P<0.01)", "极显著(**P<0.01)"),
    ("高度显著(***P<0.001)", "高度显著(***P<0.001)"),
    ("两组对比：A组(**P<0.01)且B组(**P<0.01)", "两组对比：A组(**P<0.01)且B组(**P<0.01)"),  # 这是一个陷阱！
    ("混合测试：这是**加粗**，而这是显著性**P<0.01", "混合测试：这是加粗，而这是显著性**P<0.01"),
    ("空格测试：* P<0.05", "空格测试：* P<0.05")
]

print("--- 原始逻辑测试 ---")
for raw, expected in test_cases:
    result = current_strip_bold(raw)
    status = "✅" if result == expected else f"❌ (Got: {result})"
    print(f"输入: {raw}\n期望: {expected}\n结果: {status}\n")

print("\n--- 新逻辑测试 ---")
for raw, expected in test_cases:
    result = robust_strip_bold(raw)
    status = "✅" if result == expected else f"❌ (Got: {result})"
    print(f"输入: {raw}\n期望: {expected}\n结果: {status}\n")
