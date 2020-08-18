r"""
Objects of interest such as translation surfaces loaded from encoded pickles
"""
#*********************************************************************
#  This file is part of flatsurf.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click

@click.command()
@click.option("--encoded", type=str, required=True, help="a base64 encoded surface")
def pickle(encoded):
    r"""
    Load a base64 encoded pickle
    """
    from base64 import b64decode
    from sage.all import loads
    encoded = b64decode(encoded.strip().encode('ASCII'))
    return loads(encoded)
