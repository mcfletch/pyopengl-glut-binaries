# PyOpenGL-glut-binaries

Prebuilt Windows freeglut and GLE libraries for [PyOpenGL](
https://github.com/mcfletch/pyopengl).

`OpenGL.GLUT` and `OpenGL.GLE` wrap two C libraries that Windows does not
ship. This distribution carries builds of both, so a Windows user gets them
by asking:

```
pip install PyOpenGL[glut]
```

Nothing to call and nothing to configure: PyOpenGL finds the directory itself.
A freeglut the *system* provides still wins over these, because a user who
installed their own meant it.

## Why it is a package of its own

The same builds shipped inside PyOpenGL itself, in every wheel on every
platform, so a Linux server rendering headlessly through EGL downloaded six
freeglut builds it could never load. As a separate, platform-tagged
distribution they reach the machines that can use them and no others, and a
scanner that objects to a decade-old vendored binary objects to a package only
GLUT users install rather than to PyOpenGL.

## What is here

Six builds of each library, because PyOpenGL asks for one exact name composed
from the running interpreter's word size and compiler generation:

| | 32-bit | 64-bit |
|---|---|---|
| **vc9** (Visual Studio 2008) | `freeglut32.vc9.dll`, `gle32.vc9.dll` | `freeglut64.vc9.dll`, `gle64.vc9.dll` |
| **vc10** (Visual Studio 2010) | `freeglut32.vc10.dll`, `gle32.vc10.dll` | `freeglut64.vc10.dll`, `gle64.vc10.dll` |
| **vc14** (Visual Studio 2015 and later) | `freeglut32.vc14.dll`, `gle32.vc14.dll` | `freeglut64.vc14.dll`, `gle64.vc14.dll` |

The `win32` and `win_amd64` wheels each carry only their six matching DLLs,
along with the upstream licence and readme files. The `win_arm64` wheel
carries exactly `freeglutarm64.vc14.dll` and `glearm64.vc14.dll`. Wheel builds
validate PE Machine values and fail on missing or wrongly labelled DLLs.
`BUILDS` describes the files actually installed, not every architecture.

### Native Windows ARM64 builds

ARM64 is built from public FreeGLUT 3.8.0 and GLE 3.1.0 source, not from the
legacy binaries or by relabelling an x64 wheel. `tools/arm64-sources.json`
pins source URLs/commits and SHA256 hashes. The build verifies every download
before extracting/compiling. Licences and the source manifest ship in the wheel.

In an **ARM64-targeting MSVC developer shell**, with Python 3.12+, CMake and
Ninja installed:

```powershell
python -m pip install build cmake ninja
python tools/build_arm64.py --work C:/build/pyopengl-arm64
python -m build --wheel -C--build-option=--plat-name=win_arm64
```

The work directory must not exist. The build uses the static MSVC runtime and
at most two compiler jobs. Where the Windows SDK omits ARM64 OpenGL/GLU import
libraries, it generates import stubs from hash-pinned mingw-w64 definitions.
The implementations are still the Windows system DLLs; no substitute graphics
implementation or foreign-architecture library is bundled. The relevant
mingw-w64 licence travels with the wheel too.

The reusable `arm64.yml` job builds on `windows-11-arm`, installs into fresh
CPython 3.11 and 3.14 environments (the native ARM64 interpreter floor and the
suite's ceiling), then runs `tests/smoke_arm64.py` outside the checkout. It checks the
interpreter ABI, exact payload, PE Machine, licences, real DLL loads, FreeGLUT
init state and GLE state round-trips. It requires **no GPU, window or
OpenGL context** and makes no rendering claim. It runs for pull requests and
as part of the existing release test gate; its wheel artifact is collected by
the existing release publisher. No version is bumped by this change.

PyOpenGL also needs the ARM64 loader selection in
[mcfletch/pyopengl#177](https://github.com/mcfletch/pyopengl/pull/177);
this package deliberately does not duplicate that loader change.

## Using it directly

PyOpenGL is the intended caller, but the path is public:

```python
from pyopengl_glut_binaries import DLL_DIRECTORY
```

`BUILDS` lists the base names above and `LIBRARIES` says where each library
came from.

## Licensing

The packaging is BSD-licensed; see `LICENSE`. The libraries are third-party
works under their own terms, which ship beside them in
`src/pyopengl_glut_binaries/DLLS/`:

- **freeglut** — 3.0.0-1.mp for legacy x86/x64 (Martin Payne); 3.8.0 for ARM64.
  [freeglut](http://freeglut.sourceforge.net/) upstream publishes source
  rather than Windows binaries. X-Consortium licence, in
  `freeglut_COPYING.txt`.
- **GLE** — the tubing and extrusion library, built as a Windows DLL. See
  `gle_COPYING`, `gle_COPYING.src` and `gle_AUTHORS`.

## Releases

A push to `main` runs the tests; if they are green and `__version__` in
`src/pyopengl_glut_binaries/__init__.py` is not already on PyPI, the wheels and
the sdist are built and published. Bumping the version is what cuts a release.

Issues go to [the PyOpenGL tracker](https://github.com/mcfletch/pyopengl/issues).
