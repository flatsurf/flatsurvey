r"""
Translation Surfaces coming from unfoldings of n-gons

EXAMPLES::

    >>> from survey.sources.ngons import Ngon
    >>> Ngon((1, 2, 3)).translation_cover()
    TranslationSurface built from 12 polygons

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

from sage.all import cached_method

from .surface import Surface

class Ngon(Surface):
    r"""
    The translation surface coming from the unfolding of an n-gon with prescribed angles.

    EXAMPLES:

    An equilateral triangle::

        >>> S = Ngon((1, 1, 1)); S
        Ngon((1, 1, 1))
        >>> S.translation_cover()
        TranslationSurface built from 6 polygons

    """
    def __init__(self, angles, length='exact-real'):
        self.angles = angles
        self.length = length

    def reference(self):
        if len(self.angles) == 3:
            a, b, c = self.angles
            if a == b == 1: return "Veech 1989"
            if a == 1 and b == c: return "(2, b, b) of Veech for b even"
            if a == 1 and c == b + 1: return "~(2, b, b) of Veech"
            if a == 2 and c == b + 2: return "Veech 1989"
            if a == 2 and b == c: return "Veech 1989"
            if a == 1 and b == 2 and c % 2 == 1: return "Ward 1998"
            if a == 4 and b == c: return "~(2, b, b + 2) of Veech"
            if (a, b, c) in [(3, 3, 4), (2, 3, 4)]: return "Kenyon-Smillie 2000 acute triangle"
            if (a, b, c) == (3, 4, 5): return "Kenyon-Smillie 2000 acute triangle; first appeared in Veech 1989"
            if (a, b, c) == (3, 5, 7): return "Kenyon-Smillie 2000 acute triangle; first appeared in Vorobets 1996"
            if (a, b, c) == (1, 4, 7): return "Hooper 'Another Veech triangle'"

    def __repr__(self):
        return "Ngon(%r)"%(tuple(self.angles),)

    @cached_method
    def polygon(self):
        r"""
        Return an actual n-gon with concrete lengths selected.

        EXAMPLES::

            TODO: Why does this doctest not run?
            >>> Ngon((1, 1, 1)).polygon()

        """
        from pyexactreal import ExactReals
        from flatsurf import EquiangularPolygons
        E = EquiangularPolygons(*self.angles)
        if self.length == "exact-real":
            L = E.lengths_polytope()
            R = ExactReals(E.base_ring())
            from sage.all import VectorSpace, span, free_module_element
            U = L.ambient_space().subspace([])
            lengths = free_module_element(R, len(self.angles))
            for ray in L.rays():
                ray = ray.vector()
                print(ray)
                if ray not in U:
                    U += span([ray])
                    length = R.random_element() if len(lengths) else R.one()
                    print(length)
                    lengths += length * ray
                    print(lengths)
            print(E(*lengths))
            return E(*lengths)
        else:
            raise NotImplementedError(self.length)

    @cached_method
    def translation_cover(self):
        from flatsurf import similarity_surfaces
        S = similarity_surfaces.billiard(self.polygon())
        S = S.minimal_cover(cover_type="translation")
        return S

    @cached_method
    def ambient_stratum(self):
        from flatsurf import EquiangularPolygons
        E = EquiangularPolygons(*self.angles)
        return E.billiard_unfolding_stratum("half-translation", True)


@click.command()
@click.option("--angle", "-a", multiple=True, type=int, help="inner angles of the polygon in multiples of (N - 2)π/A where N is the number of vertices and A the sum of all provided angles")
@click.option("--length", type=click.Choice(["exact-real"]), default="exact-real", help="how side lengths are chosen")
def ngon(angle, length):
    r"""
    Construct an n-gon
    """
    return Ngon(angle, length)

@click.command()
@click.option("--vertices", "-n", type=int, required=True, help="number of vertices")
@click.option("--length", type=click.Choice(["exact-real"]), default="exact-real", help="how side lengths are chosen")
@click.option("--limit", type=int, default=None, help="maximum sum of angles")
@click.option("--include-literature", default=False, is_flag=True, help="include ngons described in literature")
def ngons(vertices, length, limit, include_literature):
    r"""
    Return all n-gons with the given characteristics.
    """
    from itertools import count
    for total_angle in count(start=vertices):
        if limit is not None and total_angle >= limit:
            break

        for angles in partitions(total_angle, vertices):
            # TODO: Actually, arbitrary permutations are fine.
            if angles != min(list(rotations(angles)) + list(rotations(reversed(angles)))):
                continue
            from sage.all import gcd
            if gcd(angles) != 1:
                continue

            if len(angles) == 4:
                a, b, c, d = angles
                if a == b and c == 2*a and d == 2*c:
                    # this quadrilateral is a cover of a triangle
                    continue
            # TODO: These don't have to be a < b < c < d in that order actually, i.e., we could have c < b here.
            if len(angles) == 5:
                a, b, c, d, e = angles
                if c == 2*a and d == 2*b and e == 3*c:
                    # this pentagon is a cover of a triangle
                    continue

            ngon = Ngon(angles, length)

            if not include_literature and ngon.reference(): continue

            yield ngon

def rotations(partition):
    r"""
    Return all the rotations of the list ``partition``.

    EXAMPLES::

        >>> from survey.sources.ngons import rotations
        >>> list(rotations([1, 2, 3]))
        [[1, 2, 3], [2, 3, 1], [3, 1, 2]]

    """
    partition = list(partition)
    for i in range(len(partition)):
        yield partition[i:] + partition[:i]

def partitions(total, n):
    r"""
    Return the partitions of ``total`` into ``n`` non-zero integers.

    EXAMPLES::

        >>> from survey.sources.ngons import partitions
        >>> list(partitions(3, 2))
        [[1, 2], [2, 1]]

    """
    if n == 1: yield [total]
    else:
        for a in range(1, total):
            for partition in partitions(total - a, n - 1):
                yield [a] + partition
