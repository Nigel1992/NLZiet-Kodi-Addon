#!/usr/bin/env python3
"""Build the installable ZIP from tracked addon files, excluding development files."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parent.parent
metadata = ET.parse(root / 'addon.xml').getroot()
addon_id, version = metadata.attrib['id'], metadata.attrib['version']
# Validate so a tampered addon.xml cannot escape the build directory.
if not addon_id or '/' in addon_id or '\\' in addon_id or '..' in addon_id:
    raise SystemExit('invalid addon id in addon.xml')
if not version or '/' in version or '\\' in version or '..' in version:
    raise SystemExit('invalid version in addon.xml')
# Guard against recurring defects (e.g. a stray "PY" heredoc terminator leaking
# into a Python file) before producing a release artifact.
for path in root.rglob('*.py'):
    rel = path.relative_to(root).as_posix()
    if rel.startswith('resources/lib/') and any(part in rel for part in ('urllib3/', 'certifi/', 'charset_normalizer/', 'idna/')):
        continue
    compile(path.read_text(encoding='utf-8', errors='replace'), str(path), 'exec')
    text = path.read_text(encoding='utf-8', errors='replace')
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip() == 'PY':
            raise SystemExit('stray heredoc terminator "PY" in {} (line {})'.format(rel, lineno))

output = root / 'build' / f'{addon_id}-{version}.zip'
output.parent.mkdir(exist_ok=True)
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
skip_prefixes = ('tests/', 'scripts/', '.github/', 'build/')
skip_names = {'.gitignore', 'requirements.txt', 'SHARED.lock'}
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(filter(None, files)):
        if name.startswith(skip_prefixes) or name in skip_names or name.endswith(('.zip', '.sha256')):
            continue
        archive.write(root / name, f'{addon_id}/{name}')
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert f'{addon_id}/addon.xml' in archive.namelist()
print(output)
