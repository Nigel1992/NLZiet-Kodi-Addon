"""Regression guards for the service module.

The add-on's background service (``service.py``) is executed by Kodi as a
standalone script. A recurring defect ("the PY typo") was a stray ``PY`` line
leaking into ``service.py`` (a shell heredoc terminator), which compiles
cleanly but raises ``NameError: name 'PY' is not defined`` at runtime. These
tests execute the module so such a defect fails the suite instead of shipping.
"""
import os
import sys

import pytest

ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ADDON_ROOT not in sys.path:
    sys.path.insert(0, ADDON_ROOT)


def test_service_module_imports():
    import service
    assert hasattr(service, 'main')
    assert hasattr(service, 'MONITOR')
    assert hasattr(service, 'REPEATS')


def test_default_module_imports():
    import sys
    sys.argv = ['default.py', '1']
    import default
    assert hasattr(default, 'HANDLE')


def test_no_stray_heredoc_terminator_in_python_files():
    root = ADDON_ROOT
    offenders = []
    skip_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv',
                 'node_modules', 'build'}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(dirpath, root)
        # Skip vendored third-party packages, but still scan our own modules
        # under resources/lib.
        vendored = {'certifi', 'charset_normalizer', 'idna', 'urllib3'}
        parts = rel.split(os.sep)
        if len(parts) >= 3 and parts[0] == 'resources' and parts[1] == 'lib' and parts[2] in vendored:
            continue
        for name in files:
            if not name.endswith('.py'):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding='utf-8', errors='replace') as fh:
                    for lineno, line in enumerate(fh, 1):
                        if line.strip() == 'PY':
                            offenders.append('{}:{}'.format(
                                os.path.relpath(path, root), lineno))
            except OSError:
                continue
    assert not offenders, 'Stray heredoc terminator "PY" found: ' + ', '.join(offenders)
