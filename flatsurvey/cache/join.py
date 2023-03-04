r"""
Aggregate cache files.
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
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline import Goal
from flatsurvey.command import Command
from flatsurvey.pipeline.util import PartialBindingSpec


class Join(Goal, Command):
    r"""
    Aggregate ``jsons`` into a single JSON file.

    Writes out a .json file for each type of result in the inputs.
    """
    @copy_args_to_internal_fields
    def __init__(self, jsons, prefix, report):
        super().__init__(producers=[], report=report, cache=None)

    @classmethod
    @click.command(name="join")
    @click.argument('jsons', nargs=-1, type=click.Path(exists=True))
    @click.option("--prefix", type=str, help="a common prefix for the output files", default=None)
    def click(jsons, prefix):
        return {
            "goals": [Join],
            "bindings":  [
                PartialBindingSpec(Join)(
                    jsons=jsons, prefix=prefix)
            ]
        }

    async def resolve(self):
        from collections import defaultdict
        aggregate = defaultdict(lambda: [])

        import flatsurvey.cache.cache
        for json in self._jsons:
            with open(json) as input:
                parsed = flatsurvey.cache.cache.Cache.load(input)
                for key in parsed:
                    if not isinstance(parsed[key], list):
                        raise NotImplementedError(f"cannot join entries for '{key}' because it's not list")
                    aggregate[key].extend(parsed[key])

        for key in aggregate:
            fname = f"{key}.json"

            if self._prefix:
                fname = f"{self._prefix}.{fname}"

            with open(fname, "w") as output:
                import json
                json.dump({
                    key: aggregate[key]
                }, output, indent=2)
