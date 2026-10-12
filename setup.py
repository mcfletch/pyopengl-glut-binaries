#! /usr/bin/env python3
"""A wheel that is platform-specific without holding an extension module.

The payload is prebuilt Windows DLLs, so the wheel this project produces has
to carry a platform tag: the whole reason the binaries live in a distribution
of their own is that a Linux or macOS install never downloads them, and only
the tag achieves that. setuptools decides purity from whether there are
extension modules to build, and there are none here -- the DLLs are data --
so it would produce ``py3-none-any`` and every platform would get them again.

This packages prebuilt DLLs and validates their architecture. ARM64 binaries
are compiled first by tools/build_arm64.py; metadata lives in pyproject.toml.
"""

import struct
from pathlib import Path

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
from setuptools.dist import Distribution


class BinaryDistribution(Distribution):
    """A distribution whose contents are platform-specific.

    ``has_ext_modules`` is what ``bdist_wheel`` asks, and answering yes is what
    makes the wheel's root impure and so gives it a platform tag.
    """

    def has_ext_modules(self):
        return True


class bdist_wheel(_bdist_wheel):
    """Tag the wheel for the platform but for no particular interpreter.

    The default tag for an impure wheel names the interpreter and ABI that
    built it -- ``cp313-cp313-win_amd64`` -- because that is what a compiled
    extension is tied to. A DLL loaded through ctypes is tied to neither, so
    the tag is ``py3-none-<platform>``: one wheel per platform serves every
    Python 3 rather than one per interpreter release.

    ``--plat-name`` still chooses the platform, which is how a single Windows
    runner produces both the ``win32`` and the ``win_amd64`` wheel.
    """

    def run(self):
        # Build first, then filter only the staged copy. Never remove checkout
        # DLLs: release builds package multiple architectures sequentially.
        self.run_command('build')
        platform = self.plat_name.replace('-', '_')
        targets = {
            'win32': ('32', 0x14C),
            'win_amd64': ('64', 0x8664),
            'win_arm64': ('arm64', 0xAA64),
        }
        if platform in targets:
            suffix, machine = targets[platform]
            directory = (
                Path(self.get_finalized_command('build').build_lib)
                / 'pyopengl_glut_binaries'
                / 'DLLS'
            )
            expected = {
                '%s%s.%s.dll' % (lib, suffix, vc)
                for lib in ('freeglut', 'gle')
                for vc in (('vc14',) if suffix == 'arm64' else ('vc9', 'vc10', 'vc14'))
            }
            for dll in directory.glob('*.dll'):
                if dll.name not in expected:
                    dll.unlink()
            for name in expected:
                data = (directory / name).read_bytes()
                pe = struct.unpack_from('<I', data, 0x3C)[0]
                if (
                    data[pe : pe + 4] != b'PE\0\0'
                    or struct.unpack_from('<H', data, pe + 4)[0] != machine
                ):
                    raise ValueError('Wrong PE architecture: %s' % name)
        self.skip_build = True
        super().run()

    def get_tag(self):
        _python, _abi, platform = super().get_tag()
        return 'py3', 'none', platform


setup(distclass=BinaryDistribution, cmdclass={'bdist_wheel': bdist_wheel})
