"""A platform tag must describe every PE shipped in the wheel."""

import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_arm64_tag_requires_real_arm64_binaries(tmp_path):
    if (ROOT / 'src/pyopengl_glut_binaries/DLLS/glearm64.vc14.dll').exists():
        pytest.skip('native build already staged; installed smoke validates it')
    result = subprocess.run(
        [
            sys.executable,
            'setup.py',
            'bdist_wheel',
            '--plat-name',
            'win_arm64',
            '--dist-dir',
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, 'must not relabel x86/x64 DLLs as ARM64'
    assert 'arm64.vc14.dll' in result.stderr
    assert not list(tmp_path.glob('*.whl'))


@pytest.mark.parametrize('platform,machine', [('win32', 0x14C), ('win_amd64', 0x8664)])
def test_wheel_contains_only_its_architecture(tmp_path, platform, machine):
    subprocess.run(
        [
            sys.executable,
            'setup.py',
            'bdist_wheel',
            '--plat-name',
            platform,
            '--dist-dir',
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    wheels = list(tmp_path.glob('*.whl'))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        dlls = [name for name in wheel.namelist() if name.endswith('.dll')]
        assert len(dlls) == 6
        for name in dlls:
            data = wheel.read(name)
            pe = struct.unpack_from('<I', data, 0x3C)[0]
            assert struct.unpack_from('<H', data, pe + 4)[0] == machine, name
        assert any(name.endswith('gle_COPYING.src') for name in wheel.namelist())
        assert any(name.endswith('freeglut_COPYING.txt') for name in wheel.namelist())
