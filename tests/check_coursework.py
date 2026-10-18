"""Verify the assignment HTML/CSS freeze against the published baseline."""
from pathlib import Path
import re
import json
import hashlib

root = Path(__file__).resolve().parents[1]
baseline = json.loads((root / 'tests/site_baseline.json').read_text(encoding='utf-8'))
checked = 0
for name, expected in baseline.items():
    current = (root / name).read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(current).hexdigest() == expected, f'Freeze violated: {name}'
    checked += 1

for path in (root / 'demofinal/js').glob('*.js'):
    code = path.read_text(encoding='utf-8-sig')
    assert "'use strict'" in code, path
    assert not re.search(r'\b(?:var|eval)\b|document\.write|\.innerHTML|\.style\b', code), path
    assert not re.search(r'(?<![=!])==(?!=)|(?<!!)\!=(?!=)', code), path
print(f'PASS: {checked} frozen HTML/CSS files; project JavaScript policy checks.')
