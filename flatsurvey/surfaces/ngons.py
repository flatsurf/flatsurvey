r"""
Translation Surfaces coming from unfoldings of n-gons

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "ngon", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker ngon [OPTIONS]
      Unfolding of an n-gon with prescribed angles.
    Options:
      -a, --angle INTEGER            inner angles of the polygon in multiples of (N
                                     - 2)π/A where N is the number of vertices and A
                                     the sum of all provided angles
      --length [exact-real|e-antic]  how side lengths are chosen [default: e-antic
                                     for triangles, exact-real otherwise]
      --help                         Show this message and exit.

    >>> from flatsurvey.__main__ import survey
    >>> invoke(survey, "ngons", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: survey ngons [OPTIONS]
      The translation surfaces that come from unfolding n-gons.
    Options:
      -n, --vertices INTEGER         number of vertices  [required]
      --length [exact-real|e-antic]  how side lengths are chosen  [default: e-antic
                                     for triangles, exact-real otherwise]
      --limit INTEGER                maximum sum of angles  [default: unlimited]
      --include-literature           also include ngons described in literature
                                     [default: False]
      --family TEXT                  instead of producing all n-gons up to a limited
                                     total angle, produce the family given by this
                                     expression for n = 1, …, limit, e.g., '(1, 2,
                                     7*n)' for the family (1, 2, 7), (1, 2, 14), …
      --help                         Show this message and exit.

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
        Ngon([1, 1, 1])
        >>> S.surface()
        TranslationSurface built from 2 polygons

    """
    def __init__(self, angles, length='exact-real', lengths=None):
        self.angles = list(angles)
        self.length = length
        if lengths is not None:
            self._lengths.set_cache(tuple(lengths))

        if any(a == sum(angles) / (len(angles) - 2) for a in angles):
            print("Note: This ngon has a π angle. We can handle that but this is probably not what you wanted?")

        self._name = "-".join([str(a) for a in angles])
        self._eliminate_marked_points = True

    def reference(self):
        r"""
        Return information about this surface if it has already been studied.

        EXAMPLES::

            >>> Ngon((1, 1, 12)).reference()
            'Veech 1989'

            >>> Ngon((1, 1, 1, 3)).reference()
            Note: This ngon has a π angle. We can handle that but this is probably not what you wanted?
            '(1, 1, 1)'

        """
        from sage.all import gcd

        if any(a == sum(self.angles) / (len(self.angles) - 2) for a in self.angles):
            return f"{tuple(a for a in self.angles if a != sum(self.angles) / (len(self.angles) - 2))}"

        if list(sorted(self.angles)) != list(self.angles):
            return "Same orbit closure as %s"%(tuple(sorted(self.angles)),)

        if gcd(self.angles) != 1:
            return "Same as %s"%(tuple(a / gcd(self.angles) for a in self.angles),)

        if len(self.angles) == 3:
            a, b, c = self.angles
            assert a <= b <= c
            if a == b == 1: return "Veech 1989"
            if a == b: return "Same as (%d, %d, %d)"%(2*a, c, 2*a+c)
            if b == c: return "Same as (%d, %d, %d)"%(2*b, a, 2*b+a)
            if a == 1 and c == b + 1: return "~(2, b, b) of Veech"
            if a == 2 and c == b + 2: return "Veech 1989"
            if a == 1 and b == 2 and c % 2 == 1: return "Ward 1998"
            if (a, b, c) == (2, 3, 4): return "Kenyon-Smillie 2000 acute triangle"
            if (a, b, c) == (3, 4, 5): return "Kenyon-Smillie 2000 acute triangle; first appeared in Veech 1989"
            if (a, b, c) == (3, 5, 7): return "Kenyon-Smillie 2000 acute triangle; first appeared in Vorobets 1996"
            if (a, b, c) == (1, 4, 7): return "Hooper 'Another Veech triangle'"
            if (a, b, c) in [(1, 3, 6), (1, 3, 8)]: return "Rank-one example (to be checked)"

        if len(self.angles) == 4:
            a, b, c, d = self.angles
            assert a <= b <= c <= d
            if (a, b, c, d) == (1, 1, 1, 7): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 1, 9): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 2, 8): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 2, 12): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 2, 2, 11): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 2, 2, 15): return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 1, 1): return "Torus"
            if a == b and c == d:
                if a % 2 != c % 2:
                    return "Same as (%d, %d, %d, %d)"%(2 * a, 2 * c, a + c, a + c)
                else:
                    return "Same as (%d, %d, %d, %d)"%(a, c, (a + c)/2, (a + c)/2)

    @property
    def orbit_closure_dimension_upper_bound(self):
        if not hasattr(self, "_bound"):
            from flatsurf import EquiangularPolygons
            self._bound = EquiangularPolygons(*self.angles).billiard_unfolding_stratum_dimension('half-translation', marked_points=not self._eliminate_marked_points)

        return self._bound

    def __repr__(self):
        return f"Ngon({self.angles})"

    def _flatsurvey_characteristics(self):
        return { "angles": [int(a) for a in self.angles] }

    @cached_method
    def _lengths(self):
        r"""
        Determine random lengths for the sides of the original n-gon.

        EXAMPLES::

            >>> Ngon((1, 2, 3))._lengths()

        """
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

            return tuple(lengths)

        for n in range(1024):
            lengths = random_lengths()
            try:
                E(lengths)
            except ValueError as e:
                continue
            while min(lengths) < 1:
                lengths = tuple(l * 2 for l in lengths)
            return lengths

        raise Exception("giving up on", E)

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
    def _surface(self):
        from flatsurf import similarity_surfaces
        S = similarity_surfaces.billiard(self.polygon(), rational=True)
        S = S.minimal_cover(cover_type="translation")
        return S

    @classmethod
    def to_yaml(cls, representer, self):
        from flatsurf.geometry.pyflatsurf_conversion import to_pyflatsurf

        surface = to_pyflatsurf(self.surface())
        representer.add_representer(type(surface), type(surface).to_yaml)

        return representer.represent_data({
            'angles': self.angles,
            'length': self.length,
            'polygon': self.polygon(),
            'translation_cover': self.surface(),
            'surface': surface,
        })

    def __reduce__(self):
        return (Ngon, (self.angles, self.length, self._lengths()))

    def __hash__(self):
        return hash((tuple(self.angles), self._lengths()))

    def __eq__(self, other):
        return isinstance(other, Ngon) and self.angles == other.angles and self._lengths() == other._lengths()

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    @click.command(name="ngon", cls=GroupedCommand, group="Surfaces", help=__doc__.split('EXAMPLES')[0])
    @click.option("--angle", "-a", multiple=True, type=int, help="inner angles of the polygon in multiples of (N - 2)π/A where N is the number of vertices and A the sum of all provided angles")
    @click.option("--length", type=click.Choice(["exact-real", "e-antic"]), required=False, help="how side lengths are chosen [default: e-antic for triangles, exact-real otherwise]")
    def click(angle, length):
        if length is None:
            if len(angle) == 3: length = "e-antic"
            else: length = "exact-real"

        return {
            "bindings": [ PartialBindingSpec(Ngon, name="surface")(angles=angle, length=length) ]
        }


class Ngons:
    r"""
    The translation surfaces that come from unfolding n-gons.
    
    EXAMPLES::
    
        >>> list(Ngons.click.callback(3, 'e-antic', 6, include_literature=True, family=None))
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3]), Ngon([2, 2, 2])]

        >>> list(Ngons.click.callback(3, 'e-antic', 6, include_literature=False, family=None))
        []

        >>> list(Ngons.click.callback(3, 'e-antic', 3, include_literature=True, family='(1, 1, n)'))
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3])]
    
        >>> list(Ngons.click.callback(3, 'e-antic', 3, include_literature=True, family='[(1, 1, n), (1, 2, 12*n)]'))
        [Ngon([1, 1, 1]), Ngon([1, 2, 12]), Ngon([1, 1, 2]), Ngon([1, 2, 24]), Ngon([1, 1, 3]), Ngon([1, 2, 36])]
    
    """
    @classmethod
    @click.command(name="ngons", cls=GroupedCommand, group="Surfaces", help=__doc__.split('EXAMPLES')[0])
    @click.option("--vertices", "-n", type=int, required=True, help="number of vertices")
    @click.option("--length", type=click.Choice(["exact-real", "e-antic"]), required=False, help="how side lengths are chosen  [default: e-antic for triangles, exact-real otherwise]")
    @click.option("--limit", type=int, default=None, help="maximum sum of angles  [default: unlimited]")
    @click.option("--count", type=int, default=None, help="number of n-gons to produce  [default: unlimited]")
    @click.option("--include-literature", default=False, is_flag=True, help="also include ngons described in literature", show_default=True)
    @click.option("--family", type=str, default=None, help="instead of producing all n-gons up to a limited total angle, produce the family given by this expression for n = 1, …, limit, e.g., '(1, 2, 7*n)' for the family (1, 2, 7), (1, 2, 14), …")
    def click(vertices, length, limit, count, include_literature, family):
        if length is None:
            if vertices == 3: length = "e-antic"
            else: length = "exact-real"

        import itertools
        for n in itertools.count(start=vertices):
            print(f"Sum of {vertices} angles {n}")
            if limit is not None and n > limit:
                break
    
            if family:
                pool = eval(family, {'n': n})
                if not isinstance(pool, list): pool = [pool]
            else:
                total_angle = n
                pool = partitions(total_angle, vertices)
    
    
            for angles in pool:
                if any(a >= 2 * sum(angles) / (len(angles) - 2) for a in angles):
                    # angles contains an angle of 2π (or more.)
                    continue
    
                if any(a == sum(angles) / (len(angles) - 2) for a in angles):
                    # an angle is π
                    continue
    
                ngon = Ngon(angles, length=length)
    
                if not include_literature and ngon.reference(): continue

                if count is not None:
                    if count <= 0: return
                    count -= 1

                yield ngon


def rotations(partition):
    r"""
    Return all the rotations of the list ``partition``.

    EXAMPLES::

        >>> from flatsurvey.surfaces.ngons import rotations
        >>> list(rotations([1, 2, 3]))
        [[1, 2, 3], [2, 3, 1], [3, 1, 2]]

    """
    partition = list(partition)
    for i in range(len(partition)):
        yield partition[i:] + partition[:i]


def partitions(total, n):
    r"""
    Return the ordered partitions of ``total`` into ``n`` non-zero integers.

    EXAMPLES::

        >>> from flatsurvey.surfaces.ngons import partitions
        >>> list(partitions(4, 2))
        [[1, 3], [2, 2]]

    """
    if n == 1: yield [total]
    else:
        for a in range(1, total):
            for partition in partitions(total - a, n - 1):
                if a <= partition[0]: yield [a] + partition
