#! /usr/bin/env python3
"""The libraries are the whole distribution, so their arrival is the whole test.

This package holds one path constant over a directory of binaries, and every
way it can fail is a file that did not arrive: at the wrong name, from a
checkout, or out of a built wheel. #127 on the PyOpenGL tracker is what that
looks like from a user's side -- a Windows install with the directory simply
absent, and no error saying anything more useful than that `glutInit` is an
undefined function.

The cases run on any platform. The DLLs cannot be *loaded* anywhere but
Windows, and loading them is PyOpenGL's job rather than this package's; what
is asked here is that they are present and named as the caller expects.

https://github.com/mcfletch/pyopengl/issues/127
"""

import os
import subprocess
import sys
import zipfile

import pytest

import pyopengl_glut_binaries as binaries

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class TestTheDirectory:
    def test_it_exists(self):
        assert os.path.isdir(binaries.DLL_DIRECTORY), binaries.DLL_DIRECTORY

    def test_it_is_absolute(self):
        """The caller joins a file name onto it from wherever it happens to
        be, so a path relative to this package's own directory would resolve
        against the caller's working directory instead."""
        assert os.path.isabs(binaries.DLL_DIRECTORY)

    def test_it_is_inside_this_package(self):
        assert binaries.DLL_DIRECTORY.startswith(
            os.path.dirname(os.path.abspath(binaries.__file__))
        )


class TestTheBuildsAreNamedAsPyOpenGLAsksForThem:
    """``OpenGL.platform.win32`` composes one exact name and asks for that.

    ``freeglut%s.%s`` over the interpreter's word size and the compiler
    generation, and the same for ``gle``. A distribution carrying eleven of
    the twelve is one that fails on a single interpreter and nowhere else, so
    the names are asserted rather than counted.
    """

    @pytest.mark.parametrize('library', ['freeglut', 'gle'])
    @pytest.mark.parametrize('size', ['32', '64'])
    @pytest.mark.parametrize('vc', ['vc9', 'vc10', 'vc14'])
    def test_the_build_is_there(self, library, size, vc):
        name = '%s%s.%s.dll' % (library, size, vc)
        assert os.path.isfile(os.path.join(binaries.DLL_DIRECTORY, name)), name

    def test_builds_lists_exactly_what_is_here(self):
        """``BUILDS`` is documentation, and documentation that drifts from the
        directory is worse than none."""
        present = sorted(
            name[: -len('.dll')]
            for name in os.listdir(binaries.DLL_DIRECTORY)
            if name.endswith('.dll')
        )
        assert sorted(binaries.BUILDS) == present


class TestTheLicencesTravelWithTheBinaries:
    """freeglut and GLE are somebody else's code; redistributing a binary
    without its licence is not a thing we may do."""

    @pytest.mark.parametrize(
        'name',
        ['freeglut_COPYING.txt', 'gle_COPYING', 'gle_COPYING.src', 'gle_AUTHORS'],
    )
    def test_the_licence_file_is_there(self, name):
        assert os.path.isfile(os.path.join(binaries.DLL_DIRECTORY, name)), name

    def test_every_library_is_accounted_for_in_libraries(self):
        assert set(binaries.LIBRARIES) == {'freeglut', 'gle'}


@pytest.fixture(scope='module')
def wheel(tmp_path_factory):
    """The wheel this checkout produces, as a list of member names.

    The cases above ask the checkout, which is not what a user receives: the
    DLLs are package data under a directory with no ``__init__.py``, so
    ``packages.find`` does not see it and only the ``package-data`` entry in
    ``pyproject.toml`` ships it. Nothing but a built artifact can say whether
    that worked.

    ``--no-build-isolation`` because the point is what *this* tree produces
    with the tools already here.
    """
    into = tmp_path_factory.mktemp('wheel')
    build = [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation']
    completed = subprocess.run(
        [*build, '--wheel-dir', str(into), '.'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    built = list(into.glob('*.whl'))
    assert len(built) == 1, built
    with zipfile.ZipFile(built[0]) as handle:
        return built[0].name, sorted(handle.namelist())


class TestWhatTheWheelShips:
    def test_every_file_in_the_directory_arrives(self, wheel):
        """Whatever is in the checkout is what a user gets; a file added there
        and not shipped is #127 happening again."""
        _name, members = wheel
        shipped = sorted(
            os.path.basename(member)
            for member in members
            if member.startswith('pyopengl_glut_binaries/DLLS/') and not member.endswith('/')
        )
        platform = _name.rsplit('-', 1)[1].removesuffix('.whl')
        suffix = {'win32': '32', 'win_amd64': '64', 'win_arm64': 'arm64'}.get(platform)
        expected = [
            name
            for name in os.listdir(binaries.DLL_DIRECTORY)
            if not name.endswith('.dll')
            or suffix is None
            or name.startswith(('freeglut' + suffix + '.', 'gle' + suffix + '.'))
        ]
        assert shipped == sorted(expected)

    def test_it_is_tagged_for_a_platform(self, wheel):
        """An ``any`` wheel is the state this distribution exists to leave:
        every platform downloading Windows binaries it cannot load."""
        name, _members = wheel
        assert not name.endswith('-any.whl'), name

    def test_it_is_not_tied_to_one_interpreter(self, wheel):
        """A DLL loaded through ctypes has no ABI to match, so one wheel per
        platform serves every Python 3 rather than one per release."""
        name, _members = wheel
        assert '-py3-none-' in name, name

    def test_py_typed_is_there(self, wheel):
        """Without it a checker ignores the annotations beside it."""
        _name, members = wheel
        assert 'pyopengl_glut_binaries/py.typed' in members
