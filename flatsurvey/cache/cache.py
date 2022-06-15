r"""
Access cached results from previous runs.

Currently, the only cache we support is a plain-text database stored in .json
files and some accompanying Python pickles. It would be fairly trivial to
change that and allow for other similar systems as well (and we at some point
supported a GraphQL backend but it turned out to be impractical.)

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "local-cache", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker local-cache [OPTIONS]
      A cache of previous results stored in local JSON files.
    Options:
      -j, --json PATH  JSON files to read cached data from; can be a glob expression
                       or a directory which is then searched recursively
      --help           Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2022 Julian Rüth
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
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


# TODO: Actually implement this.

class Cache(Command):
    r"""
    A cache of previous results stored in local JSON files.

    EXAMPLES::

        >>> from flatsurvey.cache.pickles import Pickles
        >>> Cache(pickles=Pickles(), jsons=())
        local-cache

    """

    @copy_args_to_internal_fields
    def __init__(
        self,
        pickles,
        jsons=(),
    ):
        import json

        self._results = {}
        for raw in jsons:
            for job, results in json.load(raw).items():
                self._results.setdefault(job, []).extend(results)

    @classmethod
    @click.command(
        name="local-cache",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--json",
        "-j",
        metavar="PATH",
        multiple=True,
        type=str,
        help="JSON files to read cached data from; can be a glob expression or a directory which is then searched recursively",
    )
    def click(json):
        return {
            "bindings": PartialBindingSpec(Cache)(jsons=json),
        }

    def command(self):
        return ["local-cache"] + [f"--json={json}" for json in self._jsons]

    @classmethod
    def bindings(cls, endpoint, key, region):
        return [PartialBindingSpec(Cache, name="cache")()]

    def deform(self, deformation):
        return {"bindings": Cache.bindings()}

    def results(self, job, predicate):
        from flatsurvey.cache.results import Results

        return Results(
            job=job,
            results=[
                entry
                for entry in self._results.get(job.command()[0], [])
                if predicate(entry)
            ],
        )
