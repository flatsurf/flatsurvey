r"""
Translation surfaces coming from unfoldings of n-gons

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "ngon", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: worker ngon [OPTIONS]
      Unfolding of an n-gon with prescribed angles.
    Options:
      -a, --angle INTEGER            inner angles of the polygon in multiples of (N
                                     - 2)π/A where N is the number of vertices and A
                                     the sum of all provided angles
      --length [exact-real|e-antic]  how side lengths are chosen [default: e-antic
                                     for triangles, exact-real otherwise]
      --help                         Show this message and exit.

    >>> from flatsurvey.survey import survey
    >>> invoke(survey, "ngons", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: survey ngons [OPTIONS]
      The translation surfaces that come from unfolding n-gons.
    Options:
      -n, --vertices INTEGER          number of vertices  [required]
      --length [exact-real|e-antic]   how side lengths are chosen  [default: e-antic
                                      for triangles, exact-real otherwise]
      --min INTEGER                   minimum sum of angles  [default: 0]
      --limit INTEGER                 maximum sum of angles  [default: unlimited]
      --count INTEGER                 number of n-gons to produce  [default:
                                      unlimited]
      --literature [exclude|include|only]
                                      also include ngons described in literature
                                      [default: exclude]
      --family TEXT                   instead of producing all n-gons up to a
                                      limited total angle, produce the family given
                                      by this expression for n = 1, …, limit, e.g.,
                                      '(1, 2, 7*n)' for the family (1, 2, 7), (1, 2,
                                      14), …
      --filter TEXT                   only produce the n-gons which satisfy this
                                      lambda expression, e.g., 'lambda a, b, c:
                                      (a + b + c) % 2 == 0'
      --help                          Show this message and exit.

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

import click
from sage.misc.cachefunc import cached_method

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.surfaces.surface import Surface
from flatsurvey.ui.group import GroupedCommand


class Ngon(Surface):
    r"""
    Unfolding of an n-gon with prescribed angles.

    EXAMPLES:

    An equilateral triangle::

        >>> S = Ngon((1, 1, 1)); S
        Ngon([1, 1, 1])
        >>> S.surface()
        Translation Surface in H_1(0) built from 2 equilateral triangles

    """

    def __init__(self, angles, length=None, polygon=None):
        super().__init__()

        self.angles = list(angles)

        if length is None:
            if len(self.angles) == 3:
                length = "e-antic"
            else:
                length = "exact-real"

        self.length = length

        if polygon is not None:
            if isinstance(polygon, tuple):
                # At some point we pickled the lengths of the sides instead of
                # the actual polygon. We are too lazy to make these pickles
                # work (because there are also two different flavors of those…)
                import warnings

                warnings.warn(
                    "ignoring legacy pickle of ngon; reported Ngon will have incorrect edge lengths"
                )
                polygon = self.polygon()

            self.polygon.set_cache(polygon)

        if any(a == sum(angles) / (len(angles) - 2) for a in angles):
            import logging

            logging.warning(
                "Note: This ngon has a π angle. We can handle that but this is probably not what you wanted?"
            )

        self._name = "-".join([str(a) for a in angles])

    def equivalents(self):
        from sage.all import gcd

        def ngon(angles):
            angles = tuple(sorted(angles))
            angles = tuple(a / gcd(angles) for a in angles)
            if self.polygon.cache:
                raise NotImplementedError(
                    f"Cannot translate explicit polygon from {self} when constructing equivalent surface."
                )
            return Ngon(angles, length=self.length)

        if any(a == sum(self.angles) / (len(self.angles) - 2) for a in self.angles):
            return [
                ngon(
                    a
                    for a in self.angles
                    if a != sum(self.angles) / (len(self.angles) - 2)
                )
            ]

        if list(sorted(self.angles)) != self.angles:
            return [ngon(self.angles)]

        if gcd(self.angles) != 1:
            return [ngon(tuple(a / gcd(self.angles) for a in self.angles))]

        equivalents = []

        if len(self.angles) == 3:
            a, b, c = self.angles
            if a == b or b == c:
                # (a, b, a + b) has a right angle at a + b. Adding a reflected
                # copy, we either get (b, b, 2a) or (a, a, 2b)
                if a == b:
                    if c % 2 == 0:
                        a_, b_ = c // 2, b
                    else:
                        # The sum of the angles does not go down, but we get a
                        # lexicographically smaller ngon.
                        a_, b_ = c, 2 * b
                else:
                    # Same as above just with swapped variables.
                    if a % 2 == 0:
                        a_, b_ = a // 2, b
                    else:
                        # The sum of the angles does not go down, but we get a
                        # lexicographically smaller ngon.
                        a_, b_ = a, 2 * b

                c_ = a_ + b_

                # Ignoring the marked points, the isosceles triangles may or
                # may not unfold to the same translation surface.
                # Let us assume that we unfold by turning around the vertex at
                # a. Then we need k copies such that ka ≡ 0 mod 4(a+b) which
                # corresponds to 2π. Also k must be even for the pieces to fit
                # together. If k is not divisible by 4, we must also unfold the
                # same triangle when flipped across the edge opposite to a.
                k = 4 * (a_ + b_) // gcd(a_, 4 * (a_ + b_))
                if k % 2 == 1:
                    k *= 2

                # We compare this to the unfolding of (b, b, 2a) to see whether
                # we get the same surface. Again, we unfold around the vertex
                # at 2a. We need l copies such that 2la ≡ 0 mod 4(a+b). Again l
                # must be even and again we distinguish whether l is divisible
                # by 4 or not.
                l = 4 * (a_ + b_) // gcd(2 * a_, 4 * (a_ + b_))
                if l % 2 == 1:
                    l *= 2

                # So (a, b, a+b) and (b, b, 2a) give the same surface if k = 2l
                # and k and l are the same mod 4.
                same = k == 2 * l and k % 4 == l % 4

                # However, even if this is not the same surface, the unfolding
                # is a degree two cover that is, for the purpose of the density
                # of the orbit closure, no more interesting than the quotient.
                if same or True:
                    equivalents.append(ngon((a_, b_, c_)))

            if c == a + b:
                # The inverse of the above, we can go from (a, b, a + b) to (a, a, 2b)
                k = 4 * (a + b) // gcd(a, 4 * (a + b))
                if k % 2 == 1:
                    k *= 2

                l = 4 * (a + b) // gcd(2 * a, 4 * (a + b))
                if l % 2 == 1:
                    l *= 2

                same = k == 2 * l and k % 4 == l % 4
                if same or True:
                    equivalents.append(ngon((a, a, 2 * b)))

        if len(self.angles) == 4:
            a, b, c, d = self.angles
            assert a <= b <= c <= d

            from itertools import permutations

            for a, b, c, d in permutations(self.angles):
                if c == sum(self.angles) / 4 and d == c:
                    # The quadrilateral contains two angles pi/2. Unfold at the edge connecting them.
                    return [
                        ngon(
                            (
                                a,
                                a,
                                b,
                                b,
                            )
                        )
                    ]

        return equivalents

    @property
    def unfolding_symmetries(self):
        r"""
        Return the symmetries of this polygon that are present in the unfolding
        as orthogonal matrices.

        This does not include symmetries of the polygon itself.

        EXAMPLES::

            >>> S = Ngon((1, 1, 1))
            >>> S.unfolding_symmetries
            {[  -1/2  1/2*c]
            [-1/2*c   -1/2], [1 0]
            [0 1], [  -1/2 -1/2*c]
            [ 1/2*c   -1/2]}

        ::

            >>> S = Ngon((1, 1, 2))
            >>> S.unfolding_symmetries
            {[1 0]
            [0 1], [ 0  1]
            [-1  0], [ 0 -1]
            [ 1  0], [-1  0]
            [ 0 -1]}

        """
        S = self._surface()

        symmetries = set()

        assert (0, 1, 0) in S.labels()

        for (sign, x, y) in S.labels():
            from sage.all import matrix

            symmetries.add(
                matrix(
                    [
                        [x, y],
                        [-y, x],
                    ],
                    immutable=True,
                )
            )

        return symmetries

    def _reference(self):
        if len(self.angles) == 3:
            a, b, c = self.angles
            assert a <= b <= c

            if a == 1 and b == 2 and c % 2 == 1:
                return "Ward 1998"
            if a == 1 and c == b + 1:
                return f"Regular {2*(b + 1)}-gon"
            if a == 2 and c == b + 2:
                return "Veech 1989"

            if (a, b, c) == (1, 4, 7):
                return "Hooper 'Another Veech triangle'"
            if (a, b, c) == (1, 4, 11):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c) == (1, 4, 15):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c) == (2, 3, 4):
                return "Kenyon-Smillie 2000 acute triangle"
            if (a, b, c) == (3, 4, 5):
                return (
                    "Kenyon-Smillie 2000 acute triangle; first appeared in Veech 1989"
                )
            if (a, b, c) == (3, 5, 7):
                return "Kenyon-Smillie 2000 acute triangle; first appeared in Vorobets 1996"
            if (a, b, c) == (1, 3, 6):
                return "Delecroix-Rüth-Wright 'A new orbit closure in genus 8'"
            if (a, b, c) == (1, 3, 8):
                return "Delecroix-Rüth-Wright 'A new orbit closure in genus 8'"
            if (a, b, c) == (3, 4, 13):
                return "Delecroix-Rüth-Wright 'A new orbit closure in genus 8'"

        if len(self.angles) == 4:
            a, b, c, d = self.angles
            assert a <= b <= c <= d

            if (a, b, c, d) == (1, 1, 1, 1):
                return "Torus"
            if (a, b, c, d) == (1, 1, 1, 7):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 1, 9):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 2, 8):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 1, 2, 12):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 2, 2, 11):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (1, 2, 2, 15):
                return "Eskin-McMullen-Mukamel-Wright 'Billiards, Quadrilaterals, and Moduli Spaces'"
            if (a, b, c, d) == (2, 2, 3, 13):
                return "Delecroix-Rüth-Wright 'A new orbit closure in genus 8'"

    def reference(self, algorithm="sum"):
        r"""
        Return information about this surface if it has already been studied.

        EXAMPLES:

        Trivial simplifications::

            >>> Ngon((1, 1, 1, 3)).reference()  # Note that this will print a warning about the π angle to the console.
            Ngon([1, 1, 1])

            >>> Ngon((2, 1, 1)).reference()
            Ngon([1, 1, 2])

            >>> Ngon((2, 2, 2)).reference()
            Ngon([1, 1, 1])

        Well known cases::

            >>> Ngon((1, 1, 2)).reference()
            'Regular 4-gon'

            >>> Ngon((1, 1, 1, 1)).reference()
            'Torus'

        Instances from the literature::

            >>> Ngon((1, 1, 12)).reference()
            'Regular 14-gon via Ngon([1, 6, 7])'

        More complicated simplifications::

            >>> Ngon((2, 3, 5)).reference()
            Ngon([1, 1, 3])

            >>> Ngon((3, 4, 7)).reference()
            Ngon([3, 3, 8])

            >>> Ngon((2, 3, 3)).reference()
            Ngon([1, 3, 4])

            >>> Ngon((4, 5, 5, 6)).reference()
            Ngon([2, 2, 3, 3])

            >>> Ngon((1, 2, 2, 3)).reference()
            Ngon([1, 1, 3, 3])

        """
        if algorithm is None:
            algorithm = "sum"

        if algorithm == "A2":
            if list(sorted(self.angles)) != self.angles:
                return "not admissible"

            from sage.all import gcd

            if gcd(self.angles) != 1:
                return "not admissible"

            if any((len(self.angles) - 2) * a == sum(self.angles) for a in self.angles):
                return "not admissible"

            if len(self.angles) == 3:
                a, b, c = self.angles
                if a == b or b == c:
                    return "reducible"

            if len(self.angles) == 4:
                a, b, c, d = self.angles
                if a == b and c == d:
                    return "reducible"

            return self._reference()

        elif algorithm == "sum":

            def better(gon):
                if gon is None:
                    return False
                if isinstance(gon, str):
                    return True
                if (
                    list(sorted(gon.angles)) == gon.angles
                    and list(sorted(self.angles)) != self.angles
                ):
                    return True
                if sum(gon.angles) < sum(self.angles):
                    return True
                if sum(gon.angles) == sum(self.angles) and tuple(gon.angles) < tuple(
                    self.angles
                ):
                    return True
                return False

            for equivalent in self.equivalents():
                if better(equivalent):
                    return equivalent

            if self._reference():
                return self._reference()

            seen = set()
            queue = [self]

            while queue:
                top = queue.pop()

                reference = top._reference()
                if reference:
                    return f"{reference} via {top}"

                if better(top):
                    return top

                if tuple(top.angles) in seen:
                    continue
                seen.add(tuple(top.angles))

                for equivalent in top.equivalents():
                    queue.append(equivalent)

    @property
    def orbit_closure_dimension_upper_bound(self):
        if not hasattr(self, "_bound"):
            angles = self.angles

            if len(angles) == 3:
                a, b, c = angles
                if a == b:
                    # An isosceles triangles is a double cover of its half.
                    angles = (2 * a, a + b + c, c)
                elif b == c:
                    # An isosceles triangles is a double cover of its half.
                    angles = (a, 2 * b, a + b + c)

            from flatsurf import EuclideanPolygonsWithAngles

            self._bound = EuclideanPolygonsWithAngles(
                *angles
            ).billiard_unfolding_stratum_dimension(
                "half-translation", marked_points=not self._eliminate_marked_points
            )

        return self._bound

    def __repr__(self):
        return f"Ngon({self.angles})"

    def _flatsurvey_characteristics(self):
        return {"angles": [int(a) for a in self.angles]}

    def cache_predicate(self, exact, cache=None):
        def surface_predicate(surface):
            if surface.type != "Ngon":
                return False
            if surface.angles != self.angles:
                return False

            if exact:
                raise NotImplementedError("exact filtering is not supported yet")

            return True

        if cache is not None:
            surfaces = set(
                [surface.pickle for surface in cache.get("surface", surface_predicate)]
            )

            def predicate(result):
                surface = result.surface
                from flatsurvey.cache.node import ReferenceNode

                if isinstance(surface, ReferenceNode):
                    return surface.pickle in surfaces
                return surface_predicate(surface)

        else:

            def predicate(result):
                return surface_predicate(result.surface)

        return predicate

    @cached_method
    def polygon(self):
        r"""
        Return an actual n-gon with concrete lengths selected.

        EXAMPLES::

            >>> Ngon((1, 1, 1)).polygon()  # doctest: +ELLIPSIS
            Polygon(vertices=[(0, 0), (..., 0), (..., ...)])

        """
        from flatsurf import EuclideanPolygonsWithAngles

        E = EuclideanPolygonsWithAngles(*self.angles)
        if self.length == "exact-real":
            # sage-flatsurf does not support random_element() with exact-real lengths
            raise NotImplementedError("exact-real ngons are currently not supported")
        elif self.length == "e-antic":
            pass
        else:
            raise NotImplementedError(self.length)

        return E.random_element()

    @cached_method
    def _surface(self):
        from flatsurf import similarity_surfaces

        S = similarity_surfaces.billiard(self.polygon())
        S = S.minimal_cover(cover_type="translation")
        return S

    @classmethod
    def to_yaml(cls, representer, self):
        from flatsurf.geometry.pyflatsurf_conversion import to_pyflatsurf

        surface = to_pyflatsurf(self.surface())
        representer.add_representer(type(surface), type(surface).to_yaml)

        return representer.represent_data(
            {
                "angles": self.angles,
                "length": self.length,
                "polygon": self.polygon(),
                "translation_cover": self.surface(),
                "surface": surface,
            }
        )

    def __reduce__(self):
        return (Ngon, (self.angles, self.length, self.polygon()))

    def __hash__(self):
        return hash((tuple(self.angles), self.polygon()))

    def __eq__(self, other):
        return (
            isinstance(other, Ngon)
            and self.angles == other.angles
            and self.polygon() == other.polygon()
        )

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    @click.command(
        name="ngon",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--angle",
        "-a",
        multiple=True,
        type=int,
        help="inner angles of the polygon in multiples of (N - 2)π/A where N is the number of vertices and A the sum of all provided angles",
    )
    @click.option(
        "--length",
        type=click.Choice(["exact-real", "e-antic"]),
        required=False,
        help="how side lengths are chosen [default: e-antic for triangles, exact-real otherwise]",
    )
    def click(angle, length):
        if length is None:
            if len(angle) == 3:
                length = "e-antic"
            else:
                length = "exact-real"

        return {
            "bindings": [
                PartialBindingSpec(Ngon, name="surface")(angles=angle, length=length)
            ]
        }


class Ngons:
    r"""
    The translation surfaces that come from unfolding n-gons.

    EXAMPLES::

        >>> list(Ngons.click.callback(3, 'e-antic', min=0, limit=None, count=6, literature='include', family=None, filter=None))
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> list(Ngons.click.callback(3, 'e-antic', min=0, limit=None, count=6, literature='include', family=None, filter=None))
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> list(Ngons.click.callback(3, 'e-antic', min=0, limit=None, count=3, literature='include', family=None, filter='lambda a, b, c: (a + b + c) % 2 == 0'))
        [Ngon([1, 1, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> list(Ngons.click.callback(3, 'e-antic', min=0, limit=None, count=3, literature='include', family='(1, 1, n)', filter=None))
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3])]

        >>> list(Ngons.click.callback(3, 'e-antic', min=0, limit=None, count=3, literature='include', family='[(1, 1, n), (1, 2, 12*n)]', filter=None))
        [Ngon([1, 1, 1]), Ngon([1, 2, 12]), Ngon([1, 1, 2])]

    """

    @classmethod
    @click.command(
        name="ngons",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--vertices", "-n", type=int, required=True, help="number of vertices"
    )
    @click.option(
        "--length",
        type=click.Choice(["exact-real", "e-antic"]),
        required=False,
        help="how side lengths are chosen  [default: e-antic for triangles, exact-real otherwise]",
    )
    @click.option(
        "--min", type=int, default=0, help="minimum sum of angles  [default: 0]"
    )
    @click.option(
        "--limit",
        type=int,
        default=None,
        help="maximum sum of angles  [default: unlimited]",
    )
    @click.option(
        "--count",
        type=int,
        default=None,
        help="number of n-gons to produce  [default: unlimited]",
    )
    @click.option(
        "--literature",
        default="exclude",
        type=click.Choice(["exclude", "include", "only"]),
        help="also include ngons described in literature",
        show_default=True,
    )
    @click.option(
        "--family",
        type=str,
        default=None,
        help="instead of producing all n-gons up to a limited total angle, produce the family given by this expression for n = 1, …, limit, e.g., '(1, 2, 7*n)' for the family (1, 2, 7), (1, 2, 14), …",
    )
    @click.option(
        "--filter",
        type=str,
        default=None,
        help="only produce the n-gons which satisfy this lambda expression, e.g., 'lambda a, b, c: (a + b + c) % 2 == 0'",
    )
    def click(vertices, length, min, limit, count, literature, family, filter):
        if length is None:
            if vertices == 3:
                length = "e-antic"
            else:
                length = "exact-real"

        if filter is not None:
            if not callable(filter):
                filter = eval(filter, {})

        import itertools

        for n in itertools.count(start=min):
            if limit is not None and n > limit:
                break

            if family:
                pool = eval(family, {"n": n})
                if not isinstance(pool, list):
                    pool = [pool]
            else:
                total_angle = n
                pool = partitions(total_angle, vertices)

            for angles in pool:
                if any(a <= 0 for a in angles):
                    continue

                if any(a >= 2 * sum(angles) / (len(angles) - 2) for a in angles):
                    # angles contains an angle of 2π (or more.)
                    continue

                if any(a == sum(angles) / (len(angles) - 2) for a in angles):
                    # an angle is π
                    continue

                from sage.all import gcd

                if gcd(angles) != 1:
                    continue

                if filter is not None:
                    if not filter(*angles):
                        continue

                ngon = Ngon(angles, length=length)

                if literature == "include":
                    pass
                elif literature == "exclude":
                    if ngon.reference():
                        continue
                elif literature == "only":
                    reference = ngon.reference()
                    if reference is None or reference in [
                        "not admissible",
                        "reducible",
                    ]:
                        continue
                else:
                    raise NotImplementedError("Unsupported literature value")

                if count is not None:
                    if count <= 0:
                        return
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
    if n == 1:
        yield [total]
    else:
        for a in range(1, total):
            for partition in partitions(total - a, n - 1):
                if a <= partition[0]:
                    yield [a] + partition


__test__ = {
    # Work around https://trac.sagemath.org/ticket/33951
    "Ngon._polygon": Ngon.polygon.__doc__,
    # Work around https://trac.sagemath.org/ticket/33951
    "Ngon._surface": Ngon._surface.__doc__,
}
