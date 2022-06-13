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


# TODO: Actually implement this.

class Pickles:
    @classmethod
    @click.command(
        name="pickles",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("EXAMPLES")[0],
    )
    def click(self):
        return {
            "bindings": Pickles.bindings(),
        }

    @classmethod
    def bindings(cls):
        return [PartialBindingSpec(Pickles)()]
