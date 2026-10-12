"""Build public, hash-pinned FreeGLUT/GLE sources in an ARM64 MSVC environment.

Requires Python >=3.12, CMake and Ninja. Run from the repository root.
The work directory must be new: no cached binaries enter this build.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = "gleExtrusion gleGetNumSides gleSetJoinStyle glePolyCylinder gleSpiral gleSetNumSides uview_direction gleScrew gleHelicoid gleToroid gleTextureMode gleSuperExtrusion gleLathe gleGetJoinStyle glePolyCone gleTwistExtrusion urot_omega rot_about_axis urot_prince rot_prince urot_about_axis rot_omega rot_axis uviewpoint urot_axis".split()


def run(args, cwd):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    manifest = ROOT / 'tools/arm64-sources.json'
    for name, source in json.loads(manifest.read_text()).items():
        data = urllib.request.urlopen(source['url'], timeout=120).read()
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise ValueError('SHA256 mismatch: ' + name)
        (work / name).write_bytes(data)
    for name in ('freeglut.tar.gz', 'gle.tar.gz'):
        with tarfile.open(work / name) as archive:
            archive.extractall(work, filter='data')
    freeglut = next(work.glob('freeglut-*'))
    gle = work / 'gle-3.1.0'
    imports = work / 'imports'
    imports.mkdir()
    # The ARM64 Windows SDK may omit these import libraries. These are import
    # stubs only, not OpenGL/GLU implementations; Windows supplies both DLLs.
    for lib in ('opengl32', 'glu32'):
        run(['lib', '/NOLOGO', '/MACHINE:ARM64', '/DEF:' + str(work / (lib + '.def')),
             '/OUT:' + str(imports / (lib + '.lib'))], work)
    os.environ['LIB'] = str(imports) + ';' + os.environ['LIB']
    build = work / 'freeglut-build'
    run(['cmake', '-S', freeglut, '-B', build, '-G', 'Ninja',
         '-DCMAKE_SYSTEM_NAME=Windows', '-DCMAKE_SYSTEM_PROCESSOR=ARM64',
         '-DCMAKE_C_COMPILER=cl',
         '-DFREEGLUT_BUILD_DEMOS=OFF', '-DFREEGLUT_BUILD_STATIC_LIBS=OFF',
         '-DFREEGLUT_BUILD_SHARED_LIBS=ON',
         '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'], work)
    run(['cmake', '--build', build, '--parallel', '2'], work)
    for destination in (gle / 'config.h', gle / 'src/config.h'):
        shutil.copy2(gle / 'ms-visual-c/config.h', destination)
    src = gle / 'src'
    run(['cl', '/nologo', '/c', '/O2', '/DWIN32', '/D_WINDLL', '/Gd', '/MT',
         *sorted(src.glob('*.c'))], src)
    run(['link', '/NOLOGO', '/DLL', '/MACHINE:ARM64', '/OUT:glearm64.vc14.dll',
         *['/EXPORT:' + name for name in EXPORTS], 'opengl32.lib', 'glu32.lib',
         *sorted(src.glob('*.obj'))], src)
    output = ROOT / 'src/pyopengl_glut_binaries/DLLS'
    dlls = list(build.rglob('freeglut.dll'))
    if len(dlls) != 1:
        raise ValueError('Expected one FreeGLUT DLL: %s' % dlls)
    for source, name in [(dlls[0], 'freeglutarm64.vc14.dll'),
                         (src / 'glearm64.vc14.dll', 'glearm64.vc14.dll'),
                         (freeglut / 'COPYING', 'freeglut_COPYING.txt'),
                         (gle / 'COPYING', 'gle_COPYING'),
                         (gle / 'src/COPYING.src', 'gle_COPYING.src'),
                         (gle / 'AUTHORS', 'gle_AUTHORS'),
                         (work / 'mingw-COPYING', 'mingw_COPYING'),
                         (manifest, 'arm64-sources.json')]:
        shutil.copy2(source, output / name)


if __name__ == '__main__':
    main()
