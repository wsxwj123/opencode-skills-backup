#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

VALID = {'拒稿', '大修', '小修', '接收'}
PH_RE = re.compile(r"{{\s*[A-Z0-9_]+\s*}}")

def text_of_id(html: str, element_id: str):
    m = re.search(rf'id="{re.escape(element_id)}"[^>]*>(.*?)</', html, flags=re.S)
    if not m:
        return None
    text = re.sub(r'<[^>]+>', '', m.group(1))
    return text.strip()

def normalize(v: str | None):
    if v is None:
        return None
    return v.replace('{', '').replace('}', '').strip()

def main():
    ap = argparse.ArgumentParser(description='Validate reviewer simulator HTML output gates.')
    ap.add_argument('html_path', help='Path to generated report html')
    args = ap.parse_args()

    p = Path(args.html_path)
    html = p.read_text(encoding='utf-8')

    errors = []

    placeholders = sorted(set(PH_RE.findall(html)))
    if placeholders:
        errors.append('Unreplaced placeholders found: ' + ', '.join(placeholders[:12]) + (' ...' if len(placeholders) > 12 else ''))

    header_verdict = normalize(text_of_id(html, 'decisionVerdict'))
    final_recommendation = normalize(text_of_id(html, 'finalRecommendationText'))

    if header_verdict not in VALID:
        errors.append(f'Invalid or missing decisionVerdict: {header_verdict!r}')
    if final_recommendation not in VALID:
        errors.append(f'Invalid or missing finalRecommendationText: {final_recommendation!r}')
    if header_verdict in VALID and final_recommendation in VALID and header_verdict != final_recommendation:
        errors.append(f'Verdict mismatch: header={header_verdict}, section10={final_recommendation}')

    if errors:
        print('VALIDATION_FAILED')
        for e in errors:
            print('- ' + e)
        raise SystemExit(1)

    print('VALIDATION_OK')
    print(f'- verdict: {header_verdict}')
    print(f'- final_recommendation: {final_recommendation}')

if __name__ == '__main__':
    main()
