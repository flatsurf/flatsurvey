r"""
Translation Surfaces coming from unfoldings of n-gons

EXAMPLES::

    >>> from survey.sources.ngons import Ngon
    >>> Ngon(1, 2, 3).translation_cover()
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
from flatsurvey.ui.group import GroupedCommand

from flatsurvey.pipeline.util import PartialBindingSpec

class Ngon(Surface):
    r"""
    Unfolding of an n-gon with prescribed angles.

    EXAMPLES:

    An equilateral triangle::

        >>> S = Ngon((1, 1, 1)); S
        Ngon((1, 1, 1))
        >>> S.translation_cover()
        TranslationSurface built from 6 polygons

    """
    def __init__(self, angles, length='exact-real', lengths=None):
        self.angles = angles
        self.length = length
        self._lengths.set_cache(lengths)

        if any(a == sum(angles) / (len(angles) - 2) for a in angles):
            print("Note: This ngon has a π angle. We can handle that but this is probably not what you wanted?")

        self._name = "-".join([str(a) for a in angles])
        self._eliminate_marked_points = True

    def reference(self):
        from sage.all import gcd

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

        if list(sorted(self.angles)) != list(self.angles):
            return "Same orbit closure as %s"%(tuple(sorted(self.angles)),)

        if gcd(self.angles) != 1:
            return "Same as %s"%(tuple(a / gcd(self.angles) for a in self.angles),)

    @property
    def orbit_closure_bound(self):
        if not hasattr(self, "_bound"):
            from flatsurf import EquiangularPolygons
            self._bound = EquiangularPolygons(*self.angles).billiard_unfolding_stratum_dimension('half-translation', marked_points=not self._eliminate_marked_points)

        return self._bound

    def __repr__(self):
        return f"Ngon({self.angles})"

    def _flatsurvey_characteristics(self):
        return {
            "angles": list(self.angles)
        }

    @cached_method
    def _lengths(self):
        from flatsurf import EquiangularPolygons
        E = EquiangularPolygons(*self.angles)
        if self.length == "exact-real":
            from pyexactreal import ExactReals
            R = ExactReals(E.base_ring())
        elif self.length == "e-antic":
            from pyeantic import RealEmbeddedNumberField
            R = RealEmbeddedNumberField(E.base_ring())
        else:
            raise NotImplementedError(self.length)

        L = E.lengths_polytope()
        def random_lengths():
            # TODO: Do this properly in sage-flatsurf
            from sage.all import VectorSpace, span, free_module_element
            from random import shuffle
            U = L.ambient_space().subspace([])
    
            lengths = free_module_element(R, len(self.angles))
            rays = list(L.rays())
            shuffle(rays)
            for ray in rays:
                ray = ray.vector()
                if ray not in U:
                    U += span([ray])
                    length = R.zero()
                    while length <= 0:
                        length = R.random_element() if lengths else R.one()
                    lengths += length * ray

            return lengths

        for n in range(1024):
            lengths = random_lengths()
            try:
                E(lengths)
            except ValueError as e:
                continue
            return lengths

        raise Exception("giving up on", E)

    def command(self):
        raise NotImplementedError

    @cached_method
    def polygon(self):
        r"""
        Return an actual n-gon with concrete lengths selected.

        EXAMPLES::

            TODO: Why does this doctest not run?
            >>> Ngon(1, 1, 1).polygon()

        """
        from flatsurf import EquiangularPolygons
        E = EquiangularPolygons(*self.angles)

        return E(self._lengths())

    @cached_method
    def translation_cover(self):
        S = self._translation_cover()
        if self._eliminate_marked_points:
            from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf, to_pyflatsurf
            S = to_pyflatsurf(S)
            S.delaunay()
            S = from_pyflatsurf(S)
            S = S.erase_marked_points()
        return S

    @cached_method
    def _translation_cover(self):
        from flatsurf import similarity_surfaces
        S = similarity_surfaces.billiard(self.polygon())
        S = S.minimal_cover(cover_type="translation")
        return S

    @cached_method
    def ambient_stratum(self):
        from flatsurf import EquiangularPolygons
        E = EquiangularPolygons(*self.angles)
        return E.billiard_unfolding_stratum("half-translation", True)

    @classmethod
    def to_yaml(cls, representer, self):
        from flatsurf.geometry.pyflatsurf_conversion import to_pyflatsurf

        surface = to_pyflatsurf(self.translation_cover())
        representer.add_representer(type(surface), type(surface).to_yaml)

        return representer.represent_data({
            'angles': self.angles,
            'length': self.length,
            'polygon': self.polygon(),
            'translation_cover': self.translation_cover(),
            'surface': surface,
        })

    def __reduce__(self):
        return (Ngon, (self.angles, self.length, self._lengths()))

    def __hash__(self):
        return hash((self.angles, self._lengths()))

    def __eq__(self, other):
        return isinstance(other, Ngon) and self.angles == other.angles and self._lengths() == other._lengths()

    def __ne__(self, other):
        return not (self == other)


@click.command(cls=GroupedCommand, group="Surfaces", help=Ngon.__doc__)
@click.option("--angle", "-a", multiple=True, type=int, help="inner angles of the polygon in multiples of (N - 2)π/A where N is the number of vertices and A the sum of all provided angles")
@click.option("--length", type=click.Choice(["exact-real", "e-antic"]), default="exact-real", help="how side lengths are chosen")
def ngon(angle, length):
    return PartialBindingSpec(Ngon, name="surface")(angles=angle, length=length)

@click.command(cls=GroupedCommand, group="Surfaces")
@click.option("--vertices", "-n", type=int, required=True, help="number of vertices")
@click.option("--length", type=click.Choice(["exact-real", "e-antic"]), default="exact-real", help="how side lengths are chosen")
@click.option("--limit", type=int, default=None, help="maximum sum of angles")
@click.option("--include-literature", default=False, is_flag=True, help="include ngons described in literature")
@click.option("--family", type=str, default=None)
def ngons(vertices, length, limit, include_literature, family):
    r"""
    Return all n-gons with the given characteristics.
    """
    from itertools import count
    for total_angle in count(start=0):
        # TODO: Do not allow angles that lead to angles >=2π.
        if limit is not None and total_angle > limit:
            break

        if family:
            pool = eval(family, {'n': total_angle})
            if not isinstance(pool, list): pool = [pool]
        else:
            pool = partitions(total_angle, vertices)


        for angles in pool:
            ngon = Ngon(angles, length=length)

            if any(a >= 2 * sum(angles) / (len(angles) - 2) for a in angles):
                # angles contains an angle of 2π (or more.)
                continue

            if any(a == sum(angles) / (len(angles) - 2) for a in angles):
                # an angle is π
                continue

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
