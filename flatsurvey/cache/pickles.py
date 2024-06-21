r"""
Access a database of pickles storing parts of previous computations.

This modules supplements :module:`flatsurvey.cache.Cache`. The cache in JSON
files contains references to pickles. These pickles are resolved here.

Currently, this is mostly a placeholder. We have lots of pickles from previous
runs but unpickling them is not implemented in much generality, see #10.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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

import click

from flatsurvey.command import Command
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand


class Pickles(Command):
    def __init__(self, providers=()):
        self._providers = [PickleProvider.make(provider) for provider in providers]

    @classmethod
    @click.command(
        name="pickles",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--dir",
        "-d",
        metavar="PATH",
        multiple=True,
        type=str,
        help="local directory to search for pickles",
    )
    def click(dir):
        providers = [DirectoryPickleProvider(d) for d in dir]

        return {
            "bindings": Pickles.bindings(providers=providers),
        }

    def command(self):
        return ["pickles"] + [provider.command() for provider in self._providers]

    @classmethod
    def bindings(cls, providers):
        return [PartialBindingSpec(Pickles, scope="SHARED")(providers=providers)]

    def unpickle(self, pickle, kind):
        for provider in self._providers:
            try:
                unpickled = provider.unpickle(pickle, kind)
            except KeyError:
                continue

            return unpickled

        raise KeyError(pickle)


class PickleProvider:
    @staticmethod
    def make(data):
        if isinstance(data, bytes):
            return StaticPickleProvider(data)

        raise NotImplementedError("PickleProvider.make() has not been implemented yet")

    def load(self, raw):
        # Work around some current problems in many of our pickles:
        # - Pickles import sage.rings.number_field but SageMath cannot handle
        #   this so we get a circular import. See #10.
        from pickle import loads

        # - Pickles use cppyy.gbl.flatsurf but it's not available yet somehow. See #10.
        import pyflatsurf
        import sage.all

        try:
            return loads(raw)
        except Exception:
            raise Exception(f"Failed to unpickle {raw}")


class StaticPickleProvider(PickleProvider):
    def __init__(self, data):
        self._pickle = data

        from hashlib import sha256

        sha = sha256()
        sha.update(data)
        self._digest = sha.hexdigest()

    def unpickle(self, digest, kind):
        if digest == self._digest:
            return self.load(self._pickle)
        raise KeyError(digest)


class DirectoryPickleProvider(PickleProvider):
    def __init__(self, path):
        raise NotImplementedError("DirectoryPickleProvider not implemented yet")


class GitHubPickleProvider(PickleProvider):
    def __init__(self, organization, project):
        raise NotImplementedError("GitHubPickleProvider not implemented yet")
