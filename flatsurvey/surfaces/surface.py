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

from abc import ABC, abstractmethod
from typing import Any, Callable

from sage.misc.cachefunc import cached_method

from flatsurvey.cache import Cache


class Surface(ABC):
    r"""
    Abstract base class for translation surfaces.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> isinstance(Ngon((1, 1, 1)), Surface)
        True

    """

    def __init__(self, eliminate_marked_points=True):
        self._eliminate_marked_points = eliminate_marked_points

    def reference(self) -> "Surface | str | None":
        r"""
        Return a literature reference where this surface has been studied, a
        practically identical (but simpler) surface, or ``None``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> Ngon((1, 1, 3)).reference()
            'Veech 1989 via Ngon([2, 3, 5])'
            >>> Ngon((10, 11, 82)).reference() is None
            True

        """
        return None

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
        raise NotImplementedError

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

    @abstractmethod
    def cache_predicate(
        self, exact: bool, cache: Cache | None = None
    ) -> Callable[[Any], bool]:
        r"""
        Return a predicate that can be used to filter cache rows for this surface.

        Each result stored in the cache is going to be filtered through this
        predicate to determine whether the result actually applies to this
        surface.

        INPUT:

        - ``exact`` -- whether to only match results that have been obtained
          for the exact same surface, e.g., when given two polygon unfolding,
          whether the exact side lengths must match (or just the angles
          involved.)

        - ``cache`` -- the cache for which this predicate is going to be used
          (or ``None`` to obtain a generic predicate.)

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1, 1))

            >>> class CacheSurface:
            ...     def __init__(self, surface):
            ...         self.type = type(surface).__name__
            ...         self.angles = surface.angles

            >>> class CacheRow:
            ...     def __init__(self, surface):
            ...         self.surface = CacheSurface(surface)

            >>> predicate = surface.cache_predicate(exact=True)
            >>> predicate(CacheRow(surface))
            Traceback (most recent call last):
            ...
            NotImplementedError: exact filtering is not supported yet

            >>> predicate = surface.cache_predicate(exact=False)
            >>> predicate(CacheRow(surface))
            True

        """

    @property
    def symmetries(self):
        r"""
        Return rotational symmetries of this surface as orthogonal
        matrices.

        The symmetries returned should be such that it is usually enough to
        explore the surface in one surface and one does not gain much
        information by exploring into the directions related by symmetry.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon

            >>> S = Ngon((1, 1, 1))
            >>> S.symmetries
            {[  -1/2  1/2*c]
            [-1/2*c   -1/2], [1 0]
            [0 1], [  -1/2 -1/2*c]
            [ 1/2*c   -1/2]}

        """
        from sage.all import matrix

        return {matrix([[1, 0], [0, 1]], immutable=True)}

    @property
    def fundamental_sector(self):
        r"""
        Return a fundamental sector of the plane module the :meth:`symmetries`.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon

            >>> S = Ngon((1, 1, 1))
            >>> S.fundamental_sector
            ((1, 0), (-1/2, 1/2*c))

        ::

            >>> S = Ngon((1, 1, 2))
            >>> S.fundamental_sector
            ((1, 0), (0, 1))

        """
        positive_rotations = [Q for Q in self.symmetries if Q[1][0] > 0]
        if not positive_rotations:
            from sage.all import vector

            return vector((1, 0)), vector((1, 0))

        minimal_rotation = max(positive_rotations, key=lambda Q: Q[0])

        end = minimal_rotation.column(0)
        begin = end.parent()((1, 0))
        return begin, end

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
            {'angles': [1, 2, 3], 'genus': 1}

        """
        return {}


__test__ = {
    # Work around https://trac.sagemath.org/ticket/33951
    "Surface.surface": Surface.surface.__doc__,
}
