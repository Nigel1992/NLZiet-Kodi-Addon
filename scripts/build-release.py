#!/usr/bin/env python3
"""Build the installable ZIP from tracked addon files, excluding development files."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parent.parent
metadata = ET.parse(root / 'addon.xml').getroot()
addon_id, version = metadata.attrib['id'], metadata.attrib['version']
output = root / 'build' / f'{addon_id}-{version}.zip'
output.parent.mkdir(exist_ok=True)
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
skip_prefixes = ('tests/', 'scripts/', '.github/', 'build/')
skip_names = {'.gitignore', 'requirements.txt'}
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(filter(None, files)):
        if name.startswith(skip_prefixes) or name in skip_names or name.endswith(('.zip', '.sha256')):
            continue
        archive.write(root / name, f'{addon_id}/{name}')
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert f'{addon_id}/addon.xml' in archive.namelist()
print(output)
