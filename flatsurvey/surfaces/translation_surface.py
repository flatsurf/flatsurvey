# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2021 Julian Rüth
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

from flatsurvey.pipeline.util import FactoryBindingSpec, PartialBindingSpec

from flatsurvey.surfaces.surface import Surface


class TranslationSurface(Surface):
    def __init__(self, surface):
        self.__surface = surface

    def __repr__(self):
        return repr(self.__surface)

    @property
    def _eliminate_marked_points(self):
        return False

    @property
    def orbit_closure_dimension_upper_bound(self):
        if not hasattr(self, "_bound"):
            from flatsurf.geometry.gl2r_orbit_closure import GL2ROrbitClosure

            O = GL2ROrbitClosure(self.__surface)
            self._bound = O.d

        return self._bound

    def _surface(self):
        return self.__surface

    def __hash__(self):
        return hash(self.__surface)

    def __eq__(self, other):
        return (
            isinstance(other, TranslationSurface) and self.__surface == other.__surface
        )

    def __ne__(self, other):
        return not (self == other)
