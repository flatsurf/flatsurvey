r"""
Base class for translation surfaces in the survey.

EXAMPLES::

    >>> from flatsurvey.surfaces import Ngon
    >>> Surface in Ngon.mro()
    True

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

from sage.all import cached_method

class Surface:
    r"""
    Abstract base class for translation surfaces.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> isinstance(Ngon((1, 1, 1), 'exact-real'), Surface)
        True

    """
    def reference(self):
        r"""
        Return a literature reference where this surface has been studied or ``None``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').reference()
            'Veech 1989'
            >>> Ngon((10, 11, 82), 'exact-real').reference() is None
            True

        """
        return None

    @cached_method
    def orbit_closure(self):
        r"""
        Return the orbit closure of this surface (as has been determined so far.)

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').orbit_closure()
            GL(2,R)-orbit closure of dimension at least 2 in H_1(0^3) (ambient dimension 4)

        """
        from flatsurf import GL2ROrbitClosure
        return GL2ROrbitClosure(self.surface())

    @property
    def orbit_closure_dimension_upper_bound(self):
        r"""
        An upper bound for the dimension of the orbit closure of this surface.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 7, 11)).orbit_closure_dimension_upper_bound
            19

        """
        raise NotImplementedError("to be able to compute the orbit closure we need an upper bound on the dimensions")

    def flat_triangulation(self):
        r"""
        Return the underlying translation surface as a libflatsurf object.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).flat_triangulation()
            FlatTriangulationCombinatorial(vertices = (1, -3, 2, -1, 3, -2), faces = (1, 2, 3)(-1, -2, -3)) with vectors 1: ((3/2 ~ 1.5000000), (1/2*c ~ 0.86602540)), 2: (-(3/2 ~ 1.5000000), (1/2*c ~ 0.86602540)), 3: (0, -(c ~ 1.7320508))

        """
        from flatsurf.geometry.pyflatsurf_conversion import to_pyflatsurf
        return self.orbit_closure()._surface

    @cached_method
    def surface(self):
        r"""
        Return the underlying translation surface without marked points.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).surface()
            

        """
        S = self._surface()
        if self._eliminate_marked_points:
            from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf, to_pyflatsurf
            S = to_pyflatsurf(S)
            S.delaunay()
            S = from_pyflatsurf(S)
            S = S.erase_marked_points()
        return S

    def _surface(self):
        r"""
        Return a sage-flatsurf translation surface.

        This surface might have marked points. They are then taken out by ``surface()`` automatically.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1))._surface()
            TranslationSurface built from 6 polygons

        """
        raise NotImplementedError

    def command(self):
        r"""
        Return command line arguments that can be used to recreate this surface.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1), 'exact-real').command()
            ['pickle', '--base64', '...']

        """
        from base64 import b64encode
        from sage.all import dumps
        return ["pickle", "--base64", b64encode(dumps(self)).decode('ASCII').strip()]

    def basename(self):
        r"""
        Return a prefix for files such as logfiles.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 2, 3)).basename()
            ngon-1-2-3

        """
        import re
        return re.sub('[^\\w]+', '-', repr(self)).strip('-').lower()

    def __repr__(self):
        raise NotImplementedError("to be able to log results for surfaces we need a printable representation")

    def _flatsurvey_characteristics(self):
        r"""
        Return some characteristics about this surface that should show up in
        result databases to be able to filter by it easily.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 2, 3))._flatsurvey_characteristics()
            {'angles': [1, 2, 3]}

        """
        return {}
