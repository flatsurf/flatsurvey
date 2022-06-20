r"""
Access a database of pickles storing parts of previous computations.

This modules supplements :module:`flatsurvey.cache.Cache`. The cache in JSON
files contains references to pickles. These pickles are resolved here.

TODO: Examples
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

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


# TODO: Actually implement this.

class Pickles(Command):
    def __init__(self, providers):
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
        help="local directory to search for pickles"
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

        raise NotImplementedError

    def load(self, raw):
        # Work around some current problems in many of our pickles:
        # - Pickles import sage.rings.number_field but SageMath cannot handle
        #   this so we get a circular import. # TODO: open an issue
        import sage.all
        # - Pickles use cppyy.gbl.flatsurf but it's not available yet somehow. # TODO: open an issue
        import pyflatsurf

        from pickle import loads
        return loads(raw)


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
        raise NotImplementedError


class GitHubPickleProvider(PickleProvider):
    def __init__(self, organization, project):
        raise NotImplementedError
