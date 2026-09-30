#!/usr/bin/env python3
"""Validate research JSON output against fields.yaml definition."""
import argparse, json, yaml, sys

def get_field_names(fields, prefix=""):
    names = set()
    for f in fields:
        key = f"{prefix}{f['name']}" if prefix else f['name']
        names.add(key)
        if 'subfields' in f:
            names.update(get_field_names(f['subfields'], f"{key}."))
    return names

def get_json_keys(data, prefix=""):
    keys = set()
    for k, v in data.items():
        key = f"{prefix}{k}" if prefix else k
        keys.add(key)
        if isinstance(v, dict):
            keys.update(get_json_keys(v, f"{key}."))
    return keys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fields', required=True)
    parser.add_argument('-j', '--json-file', required=True)
    args = parser.parse_args()

    with open(args.fields) as f:
        field_def = yaml.safe_load(f)
    with open(args.json_file) as f:
        data = json.load(f)

    expected = get_field_names(field_def['fields'])
    actual = get_json_keys(data)
    special = {'uncertain'}
    missing = expected - actual - special
    if missing:
        print(f"FAIL: Missing fields: {sorted(missing)}")
        sys.exit(1)
    print(f"PASS: All {len(expected)} fields covered.")

if __name__ == '__main__':
    main()
