r"""
Deserializes a translation surface from a Base64 encoded pickle.

This is used internally to pass surfaces from the survey invocation to the workers.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "pickle", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker pickle [OPTIONS]
      A base64 encoded pickle.
    Options:
      --base64 TEXT  a base64 encoded surface  [required]
      --help         Show this message and exit.
    
"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2021 Julian Rüth
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
#*********************************************************************

import click

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.pipeline.util import FactoryBindingSpec

@click.command(cls=GroupedCommand, group="Surfaces")
@click.option("--base64", type=str, required=True, help="a base64 encoded surface")
def pickle(base64):
    r"""
    A base64 encoded pickle.
    """
    from base64 import b64decode
    from sage.all import loads
    encoded = b64decode(base64.strip().encode('ASCII'))
    return {
        "bindings": [ FactoryBindingSpec("surface", lambda: loads(encoded))]
    }
