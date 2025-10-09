r"""
Access a database of pickles storing parts of previous computations.

This modules supplements :module:`flatsurvey.cache.Cache`. The cache in JSON
files contains references to pickles. These pickles are resolved here.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "pickles", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: worker pickles [OPTIONS]
      Provide pickle files as referenced in the caches.
    Options:
      -d, --dir PATH  local directory to search for pickles
      --help          Show this message and exit.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022-2025 Julian Rüth
#
#  flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
# *********************************************************************

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

import click

from flatsurvey.pipeline import Bindings
from flatsurvey.ui import Command, GroupedCommand


class Pickles(Command):
    r"""
    Provide pickle files as referenced in the caches.

    INPUT:

    - ``providers`` -- a list of sources of pickle files such as a
      :class:`DirectoryPickleProvider` (default: no providers)

    EXAMPLES::

        >>> Pickles(providers=[])
        pickles

    """

    def __init__(self, providers: Iterable["PickleProvider"] = ()):
        self._providers = tuple(providers)

    @staticmethod
    @click.command(
        name="pickles",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("INPUT")[0],  # type: ignore
    )
    @click.option(
        "--dir",
        "-d",
        metavar="PATH",
        multiple=True,
        type=str,
        help="local directory to search for pickles",
    )
    @Bindings.click
    def click(bindings, dir):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Pickles.click)

        """
        providers = [DirectoryPickleProvider(Path(d)) for d in dir]

        bindings.define(scope=Pickles, providers=providers)

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``Pickles`` instance from the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> bindings = Bindings()
            >>> invoke_subcommand(Pickles.click, bindings=bindings)
            >>> Pickles.create(bindings)
            pickles

        """
        with bindings.scope(Pickles) as scoped:
            return Pickles(providers=scoped.get("providers", default=lambda: []))

    def load(self, digest: str):
        r"""
        Return the object identified by the pickle's ``digest``.

        INPUT:

        - ``digest`` -- the base64 encoded digest of the pickle, see
          :meth:`dumps`.

        EXAMPLES::

            >>> pickle, digest = PickleProvider.dumps("hello world")
            >>> pickles = Pickles(providers=[StaticPickleProvider(pickle, digest)])
            >>> pickles.load(digest)
            'hello world'
            >>> pickles.load('no-such-hash')
            Traceback (most recent call last):
            ...
            ValueError: No pickle for no-such-hash found

        """
        for provider in self._providers:
            try:
                return provider.load(digest)
            except KeyError:
                continue

        raise ValueError(f"No pickle for {digest} found")


class PickleProvider(ABC):
    r"""
    Abstract base class for resolvers of pickled data.
    """

    @abstractmethod
    def load(self, digest) -> Any:
        r"""
        Return the unpickled pickle identified by ``digest``.

        Raises a ``KeyError`` if this provider does not recognize this digest.
        """

    @staticmethod
    def loads(raw):
        r"""
        A customized implementation of pickle.loads() that works around common
        issues when dealing with flatsurf and SageMath.

        EXAMPLES::

            >>> from sage.all import ZZ
            >>> from pickle import dumps
            >>> PickleProvider.loads(dumps(ZZ))
            Integer Ring

        """
        from pickle import loads

        # Work around some current problems in many of our pickles:
        # - Pickles use cppyy.gbl.flatsurf but it's not available yet somehow. See #10.
        import pyflatsurf

        del pyflatsurf

        # - Pickles import sage.rings.number_field but SageMath cannot handle
        #   this so we get a circular import. See #10.
        import sage.all as sageall

        del sageall

        try:
            return loads(raw)
        except Exception:
            raise Exception(f"Failed to unpickle {raw}")

    @staticmethod
    def dumps(obj) -> tuple[bytes, str]:
        r"""
        Return a pickle of ``obj`` and a SHA digest of that pickle.

        EXAMPLES::

            >>> PickleProvider.dumps("hello world")
            (b'\x80\x04\x95\x0f\x00\x00\x00\x00\x00\x00\x00\x8c\x0bhello world\x94.', 'af20840d7725c3869b26f88302626794e6945c76d5846da4bf667e127f81ce72')

        """
        from hashlib import sha256
        from pickle import dumps

        pickle = dumps(obj)

        sha = sha256()
        sha.update(pickle)
        digest = sha.hexdigest()

        return pickle, digest


class StaticPickleProvider(PickleProvider):
    r"""
    Provides hard-coded pickled data for testing.

    EXAMPLES::

        >>> from pickle import dumps
        >>> provider = StaticPickleProvider(dumps("hello world"), digest="hash")
        >>> provider.load("hash")
        'hello world'

    """

    def __init__(self, data, digest):
        self._pickle = data
        self._digest = digest

    def load(self, digest):
        if digest == self._digest:
            return self.loads(self._pickle)
        raise KeyError(digest)


class DirectoryPickleProvider(PickleProvider):
    r"""
    Provides pickles from compressed files in a directory and its
    subdirectories.

    EXAMPLES::

        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as tmpdir:
        ...     tmpdir = Path(tmpdir)
        ...     dir = tmpdir / "str"
        ...     dir.mkdir()
        ...     path, digest = DirectoryPickleProvider.dump("hello world", dir)
        ...     provider = DirectoryPickleProvider(tmpdir)
        ...     provider.load(digest)
        'hello world'

    """

    SUFFIX = ".pickle.gz"

    def __init__(self, path: Path):
        self._digests = {
            fname.name[: -len(DirectoryPickleProvider.SUFFIX)]: fname
            for fname in path.rglob(f"*{DirectoryPickleProvider.SUFFIX}")
        }

    @staticmethod
    def dump(obj: Any, path: Path):
        r"""
        Write a compressed version of ``obj`` to a file in the directory
        ``path``.

        Return the full path of the compressed file and its digest. The value
        can be restored from this digest with :meth:`load`.

        EXAMPLES::

            >>> from tempfile import TemporaryDirectory
            >>> with TemporaryDirectory() as tmpdir:
            ...     tmpdir = Path(tmpdir)
            ...     DirectoryPickleProvider.dump("hello world", tmpdir)
            (PosixPath('.../af20840d7725c3869b26f88302626794e6945c76d5846da4bf667e127f81ce72.pickle.gz'), 'af20840d7725c3869b26f88302626794e6945c76d5846da4bf667e127f81ce72')

        """
        import gzip

        bytes, digest = PickleProvider.dumps(obj)

        fname = path / f"{digest}{DirectoryPickleProvider.SUFFIX}"
        with gzip.open(fname, mode="w") as compressed:
            compressed.write(bytes)

        return fname, digest

    def load(self, digest):
        r"""
        Restore the compressed pickle identified by ``digest``.

        EXAMPLES::

            >>> from tempfile import TemporaryDirectory
            >>> with TemporaryDirectory() as tmpdir:
            ...     tmpdir = Path(tmpdir)
            ...     _, digest = DirectoryPickleProvider.dump("hello world", tmpdir)
            ...     DirectoryPickleProvider(tmpdir).load(digest)
            'hello world'

        """
        import gzip

        path = self._digests[digest]
        with gzip.open(path, mode="r") as pickle:
            return self.loads(pickle.read())
