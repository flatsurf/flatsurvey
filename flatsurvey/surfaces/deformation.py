r"""
Deformations of surfaces

During an orbit closure search, it might be necessary to replace a given
surface with a deformation in the orbit closure to be able to determine the
full dimension of the orbit closure of the original surface.

EXAMPLES::

    >>> from flatsurvey.surfaces import Ngon, Deformation
    >>> from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf
    >>> from flatsurf import GL2ROrbitClosure

    >>> S = Ngon((1, 1, 1))

    >>> O = GL2ROrbitClosure(S.surface())

    >>> delta = [O.V2(v, 0).vector for v in O.lift(O.tangent_space_basis()[0])]
    >>> deformation = from_pyflatsurf((O._surface + delta).surface())

    >>> T = Deformation(deformation, S)
    >>> T
    Deformation of Ngon([1, 1, 1])

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

from flatsurvey.cache import Cache
from flatsurvey.surfaces.surface import Surface


class Deformation(Surface):
    r"""
    A surface that is considered a "deformed" version of an ``old`` original
    surface.

    Currently, we use this to move away from pathological surfaces in the orbit
    closure where our approach would never be able to determine the full
    dimension of the orbit closure.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon, Deformation
        >>> from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf
        >>> from flatsurf import GL2ROrbitClosure

        >>> S = Ngon((1, 1, 1))

        >>> O = GL2ROrbitClosure(S.surface())

        >>> delta = [O.V2(v, 0).vector for v in O.lift(O.tangent_space_basis()[0])]
        >>> deformation = from_pyflatsurf((O._surface + delta).surface())

        >>> T = Deformation(deformation, S)
        >>> T
        Deformation of Ngon([1, 1, 1])

    """

    def __init__(self, deformed: Surface, old: Surface):
        super().__init__(eliminate_marked_points=old._eliminate_marked_points)
        self._deformed = deformed
        self._old = old

    def __repr__(self):
        return f"Deformation of {self._old}"

    def _surface(self):
        r"""
        Return the underlying sage-flatsurf surface.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Deformation
            >>> from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf
            >>> from flatsurf import GL2ROrbitClosure

            >>> S = Ngon((1, 1, 1))

            >>> O = GL2ROrbitClosure(S.surface())

            >>> delta = [O.V2(v, 0).vector for v in O.lift(O.tangent_space_basis()[0])]
            >>> deformation = from_pyflatsurf((O._surface + delta).surface())

            >>> T = Deformation(deformation, S)
            >>> T.surface()
            Translation Surface in H_1(0) built from 2 isosceles triangles

        """
        return self._deformed

    def __hash__(self):
        return hash((self._deformed, self._old))

    def __eq__(self, other):
        return (
            isinstance(other, Deformation)
            and self._deformed == other._deformed
            and self._old == other._old
        )

    def cache_predicate(self, exact: bool, cache: Cache | None = None):
        r"""
        Return a predicate that can be used to filter cache rows for this surface.

        Currently, we do not want a deformation to use caches at all, so this
        is just the constant ``False``. We assume that this is a fairly random
        deformation that is not going to be present in the cache anyway.
        """
        del exact
        del cache
        return lambda _: False
