"""Installed-wheel acceptance; no window, context, GPU or display required."""

import ctypes
import struct
import sysconfig
from pathlib import Path

from pyopengl_glut_binaries import BUILDS, DLL_DIRECTORY


def main():
    assert sysconfig.get_platform() == 'win-arm64', sysconfig.get_platform()
    directory = Path(DLL_DIRECTORY)
    expected = {'freeglutarm64.vc14.dll', 'glearm64.vc14.dll'}
    assert {p.name for p in directory.glob('*.dll')} == expected
    assert {name + '.dll' for name in BUILDS} == expected
    for name in expected:
        data = (directory / name).read_bytes()
        offset = struct.unpack_from('<I', data, 0x3C)[0]
        assert data[:2] == b'MZ' and data[offset : offset + 4] == b'PE\0\0'
        assert struct.unpack_from('<H', data, offset + 4)[0] == 0xAA64
    for name in (
        'freeglut_COPYING.txt',
        'gle_COPYING',
        'gle_COPYING.src',
        'gle_AUTHORS',
        'mingw_COPYING',
        'arm64-sources.json',
    ):
        assert (directory / name).stat().st_size > 0, name
    # ARM64 uses the unified Windows calling convention.
    glut = ctypes.WinDLL(str(directory / 'freeglutarm64.vc14.dll'))
    glut.glutGet.argtypes = [ctypes.c_uint]
    glut.glutGet.restype = ctypes.c_int
    # freeglut_ext.h: GLUT_INIT_STATE is explicitly supported before init.
    # GLUT_VERSION is not: querying it before init terminates the process.
    assert glut.glutGet(0x007C) == 0
    gle = ctypes.CDLL(str(directory / 'glearm64.vc14.dll'))
    for getter, setter, value in [
        ('gleGetNumSides', 'gleSetNumSides', 24),
        ('gleGetJoinStyle', 'gleSetJoinStyle', 0x402),
    ]:
        get, put = getattr(gle, getter), getattr(gle, setter)
        get.argtypes, get.restype = [], ctypes.c_int
        put.argtypes, put.restype = [ctypes.c_int], None
        old = get()
        put(value)
        assert get() == value
        put(old)
        assert get() == old
    print(
        'PASS: installed ARM64 PE, exact payload, licences, DLL loads and native functions (no GPU)'
    )


if __name__ == '__main__':
    main()
