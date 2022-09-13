r"""
Splits cache files into smaller files.
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


class Split(Goal, Command):
    r"""
    Split ``json`` into smaller JSON files of size roughly ``limit``.
    """
    @copy_args_to_internal_fields
    def __init__(self, json, limit, report):
        super().__init__(producers=[], report=report, cache=None)

    @classmethod
    @click.command(name="split")
    @click.argument('json', nargs=1, type=click.Path(exists=True))
    @click.option('--limit', type=str, help="chunk size limit", default="32MB")
    def click(json, limit):
        return {
            "goals": [Split],
            "bindings":  [
                PartialBindingSpec(Split)(
                    json=json, limit=limit)
            ]
        }

    def run(self):
        from humanfriendly import parse_size
        limit = parse_size(self._limit)

        import flatsurvey.cache.cache
        with open(self._json) as input:
            parsed = flatsurvey.cache.cache.Cache.load(input)
            total = input.tell()

        if total <= limit:
            return

        if len(parsed) > 1:
            raise NotImplementedError("Cannot split mixed JSON files")

        key = next(iter(parsed.keys()))

        from math import ceil
        chunks = ceil(total / limit)
        chunk_size = len(parsed[key]) // chunks + 1

        assert chunk_size * chunks > len(parsed[key])
        for chunk in range(chunks):
            import os.path
            chunk_name = f"{os.path.splitext(self._json)[0]}.{chunk}.json"
            with open(chunk_name, "w") as output:
                import json as j
                j.dump({
                    key: parsed[key][chunk * chunk_size: (chunk + 1) * chunk_size]
                }, output, indent=2)
