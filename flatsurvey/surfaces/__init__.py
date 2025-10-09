r"""
Translation Surfaces and Related Structures of Interest

There are two kinds of closely related structures in this module, individual
surfaces, such as a particular unfolding of a polygon, and generators of
families of such surfaces such as unfoldings of all triangles.
"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
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

from flatsurvey.surfaces.deformation import Deformation
from flatsurvey.surfaces.ngons import Ngon, Ngons
from flatsurvey.surfaces.surface import Surface

generators = [Ngons.click]

commands = [Ngon.click]
