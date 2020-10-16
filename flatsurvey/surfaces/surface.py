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

from sage.all import cached_method

class Surface:
    r"""
    Abstract base class for translation surfaces.

    EXAMPLES::

        >>> from survey.sources.surface import Surface
        >>> from survey.sources.ngons import Ngon
        >>> isinstance(Ngon((1, 1, 1), 'exact-real'), Surface)
        True

    """
    def reference(self):
        r"""
        A literature reference where this surface has been studied or ``None``.

        EXAMPLES::

            >>> from survey.sources.ngons import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').reference()
            'Veech 1989'
            >>> Ngon((11, 10, 82), 'exact-real').reference() is None
            True

        """
        return None

    @cached_method
    def orbit_closure(self):
        r"""
        The orbit closure of this surface (as has been determined so far.)

        EXAMPLES::

            >>> from survey.sources.ngons import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').orbit_closure()
            GL(2,R)-orbit closure of dimension at least 2 in H_1(0^3) (ambient dimension 4)

        """
        from flatsurf import GL2ROrbitClosure
        return GL2ROrbitClosure(self.translation_cover())

    @property
    def orbit_closure_bound(self):
        raise NotImplementedError

    def flat_triangulation(self):
        from flatsurf.geometry.pyflatsurf_conversion import to_pyflatsurf
        return self.orbit_closure()._surface

    def command(self):
        r"""
        Return command line arguments that can be used to recreate this surface.

        EXAMPLES::

            >>> from survey.sources.ngons import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').command()
            ['pickle', '--base64', '...']

        """
        from base64 import b64encode
        from sage.all import dumps
        return ["pickle", "--base64", b64encode(dumps(self)).decode('ASCII').strip()]
