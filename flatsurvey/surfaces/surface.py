r"""
Base class for translation surfaces in the survey.

EXAMPLES::

    >>> from flatsurvey.surfaces import Ngon
    >>> Surface in Ngon.mro()
    True

"""
# *********************************************************************
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
# *********************************************************************

from abc import abstractmethod

from sage.misc.cachefunc import cached_method


class Surface:
    r"""
    Abstract base class for translation surfaces.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> isinstance(Ngon((1, 1, 1)), Surface)
        True

    """

    def __init__(self, eliminate_marked_points=True):
        self._eliminate_marked_points = eliminate_marked_points

    def reference(self):
        r"""
        Return a literature reference where this surface has been studied, a practically identical (but simpler) surface, or ``None``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 3)).reference()
            'Veech 1989 via Ngon([2, 3, 5])'
            >>> Ngon((10, 11, 82)).reference() is None
            True

        """
        return None

    # This should probably live on the OrbitClosure job and not here so
    # it is pickled correctly, see #44.
    @cached_method
    def orbit_closure(self):
        r"""
        Return the orbit closure of this surface (as has been determined so far.)

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).orbit_closure()
            GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2)

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
        raise NotImplementedError(
            "to be able to compute the orbit closure we need an upper bound on the dimensions"
        )

    def flat_triangulation(self):
        r"""
        Return the underlying translation surface as a libflatsurf object.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).flat_triangulation()  # doctest: +ELLIPSIS
            FlatTriangulationCombinatorial(vertices = (1, -3, 2, -1, 3, -2), faces = (1, 2, 3)(-1, -2, -3)) with vectors {1: (0, ...), 2: (..., ...), 3: (..., ...)}

        """
        return self.orbit_closure()._surface

    @cached_method
    def surface(self):
        r"""
        Return the underlying translation surface without marked points.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).surface()
            Translation Surface in H_1(0) built from 2 equilateral triangles

        """
        S = self._surface()
        if self._eliminate_marked_points:
            S = S.erase_marked_points()
        return S

    @abstractmethod
    def _surface(self):
        r"""
        Return a sage-flatsurf translation surface.

        This surface might have marked points. They are then taken out by ``surface()`` automatically.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1))._surface()
            Minimal Translation Cover of Genus 0 Rational Cone Surface built from 2 equilateral triangles

        """

    def command(self):
        r"""
        Return command line arguments that can be used to recreate this surface.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 1)).command()
            ['pickle', '--base64', '...']

        """
        from base64 import b64encode

        from sage.all import dumps

        return ["pickle", "--base64", b64encode(dumps(self)).decode("ASCII").strip()]

    def basename(self):
        r"""
        Return a prefix for files such as logfiles.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 2, 3)).basename()
            'ngon-1-2-3'

        """
        import re

        return re.sub("[^\\w]+", "-", repr(self)).strip("-").lower()

    def __repr__(self):
        raise NotImplementedError(
            "to be able to log results for surfaces we need a printable representation"
        )

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


__test__ = {
    # Work around https://trac.sagemath.org/ticket/33951
    "Surface.orbit_closure": Surface.orbit_closure.__doc__,
    # Work around https://trac.sagemath.org/ticket/33951
    "Surface.surface": Surface.surface.__doc__,
}
