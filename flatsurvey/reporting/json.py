# TODO: Test this for everything that calls result().
r"""
Writes results as JSON files.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "json", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker json [OPTIONS]
      Writes results as JSON files.
    Options:
      --output FILENAME  [default: derived from surface name]
      --help             Show this message and exit.

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

from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui.group import GroupedCommand


# TODO: Parse & dump the YAML?
class Json(Reporter):
    @classmethod
    @click.command(
        name="json",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--output",
        type=click.File("w"),
        default=None,
        help="[default: derived from surface name]",
    )
    def click(output):
        return {
            "bindings": [
                FactoryBindingSpec(
                    "json",
                    lambda surface: Json(
                        surface,
                        stream=output or open(f"{surface.basename()}.json", "w"),
                    ),
                )
            ],
            "reporters": [Json],
        }
