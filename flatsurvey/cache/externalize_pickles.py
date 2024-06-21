r"""
Extract pickles from cache files compressed into a separate directory.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2023 Julian Rüth
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

from flatsurvey.command import Command
from flatsurvey.pipeline import Goal
from flatsurvey.pipeline.util import PartialBindingSpec


class ExternalizePickles(Goal, Command):
    r"""
    Extract pickles from JSON files and write them compressed to a separate directory.
    """

    @copy_args_to_internal_fields
    def __init__(self, jsons, in_place, pickle_dir, report):
        super().__init__(producers=[], report=report, cache=None)

    @classmethod
    @click.command(name="externalize-pickles")
    @click.argument("jsons", nargs=-1)
    @click.option("--inplace", default=False, is_flag=True)
    @click.option("--pickles", type=click.Path(exists=True), help="output directory")
    def click(jsons, inplace, pickles):
        return {
            "goals": [ExternalizePickles],
            "bindings": [
                PartialBindingSpec(ExternalizePickles)(
                    jsons=jsons, in_place=inplace, pickle_dir=pickles
                )
            ],
        }

    async def resolve(self):
        def externalize(json):
            if isinstance(json, dict):
                if "pickle" in json:
                    value = json["pickle"]

                    if len(value) > 128:
                        import hashlib

                        hash = hashlib.md5(value.encode("utf-8")).hexdigest()

                        import os.path

                        fname = os.path.join(self._pickle_dir, f"{hash}.pickle.gz")

                        import gzip

                        with gzip.open(fname, mode="w") as compressed:
                            compressed.write(value.encode("ascii"))

                        json["pickle"] = hash

                for value in json.values():
                    externalize(value)
            if isinstance(json, list):
                for value in json:
                    externalize(value)

            return json

        from flatsurvey.cache.cache import Cache

        jsons = {fname: externalize(Cache.load(open(fname))) for fname in self._jsons}

        import json

        jsons = {fname: json.dumps(value, indent=2) for (fname, value) in jsons.items()}

        for fname, value in jsons.items():
            with open(fname, "w") as out:
                out.write(value)
