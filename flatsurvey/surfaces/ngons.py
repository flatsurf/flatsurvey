r"""
Translation surfaces coming from unfoldings of n-gons

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "ngon", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: worker ngon [OPTIONS]
      Unfolding of an n-gon with prescribed angles.
    Options:
      -a, --angle INTEGER            inner angles of the polygon in multiples of (N
                                     - 2)π/A where N is the number of vertices and A
                                     the sum of all provided angles
      --help                         Show this message and exit.

    >>> from flatsurvey.survey import survey
    >>> invoke(survey, "ngons", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: survey ngons [OPTIONS]
      The translation surfaces that come from unfolding n-gons.
    Options:
      -n, --vertices INTEGER          number of vertices  [required]
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
                                      lambda expression, e.g., 'lambda a, b, c: (a +
                                      b + c) % 2 == 0'
      --help                          Show this message and exit.

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

from typing import List

import click
from sage.misc.cachefunc import cached_method

from flatsurvey.pipeline import Bindings
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

    def __init__(self, angles, polygon=None):
        super().__init__()

        if len(angles) < 3:
            raise ValueError("n-gon must be at least a triangle")

        self.angles = list(angles)

        if polygon is not None:
            self.polygon.set_cache(polygon)  # type: ignore

        if any(a == sum(angles) / (len(angles) - 2) for a in angles):
            import logging

            logging.warning(
                "Note: This ngon has a π angle. We can handle that but this is probably not what you wanted?"
            )

        self._name = "-".join([str(a) for a in angles])

    def equivalents(self) -> List["Ngon"]:
        r"""
        Return a list of simpler ngons that are (for the purpose of orbit
        closure computations) essentially equivalent to this one.

        EXAMPLES::

            >>> S = Ngon((2, 5, 5))
            >>> S.equivalents()
            [Ngon([1, 5, 6])]

        """
        from sage.all import gcd

        def ngon(angles):
            angles = tuple(sorted(angles))
            angles = tuple(a / gcd(angles) for a in angles)
            if self.polygon.cache:  # type: ignore
                raise NotImplementedError(
                    f"Cannot translate explicit polygon from {self} when constructing equivalent surface."
                )
            return Ngon(angles)

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
    def symmetries(self):
        r"""
        Return the symmetries of this polygon that are present in the unfolding
        as orthogonal matrices.

        This does not include symmetries of the polygon itself.

        EXAMPLES::

            >>> S = Ngon((1, 1, 1))
            >>> S.symmetries
            {[  -1/2  1/2*c]
            [-1/2*c   -1/2], [1 0]
            [0 1], [  -1/2 -1/2*c]
            [ 1/2*c   -1/2]}

        ::

            >>> S = Ngon((1, 1, 2))
            >>> S.symmetries
            {[1 0]
            [0 1], [ 0  1]
            [-1  0], [ 0 -1]
            [ 1  0], [-1  0]
            [ 0 -1]}

        """
        S = self._surface()

        symmetries = set()

        assert (0, 1, 0) in S.labels()

        for _, x, y in S.labels():
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
        r"""
        Return a literature reference where exactly this ngon has been studied already.

        EXAMPLES::

            >>> S = Ngon((1, 2, 3))
            >>> S._reference()
            'Ward 1998'

        """
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
        Return a literature reference where this surface has been studied, a
        practically identical (but simpler) surface, or ``None``.

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
            queue: List[Ngon] = [self]

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
        r"""
        Return an upper bound of the dimension of the orbit closure of this
        ngon.

        EXAMPLES::

            >>> Ngon((1, 1, 1)).orbit_closure_dimension_upper_bound
            2

        """
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
        r"""
        Return compact properties of this surface that should be stored
        efficiently when storing this surface for caching.

        The :meth:`cache_predicate` is going to rely on these characteristics
        for its cache lookup.

        EXAMPLES::

            >>> Ngon((1, 1, 1))._flatsurvey_characteristics()
            {'angles': [1, 1, 1], 'genus': 1}

        """
        return {
            "angles": [int(a) for a in self.angles],
            "genus": int(self._surface().genus()),
        }

    def cache_predicate(self, exact, cache=None):
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
            >>> surface = Ngon((1, 1, 1))

            >>> class CacheSurface:
            ...     def __init__(self, surface):
            ...         self.type = type(surface).__name__
            ...         self.angles = surface.angles

            >>> class CacheRow:
            ...     def __init__(self, surface):
            ...         self.surface = CacheSurface(surface)

            >>> predicate = surface.cache_predicate(exact=True)
            >>> predicate(CacheRow(surface))
            True

            >>> predicate = surface.cache_predicate(exact=False)
            >>> predicate(CacheRow(surface))
            True

        """
        del cache

        def predicate(result):
            surface = result.surface
            if surface.type != "Ngon":
                return False
            if surface.angles != self.angles:
                return False

            if exact:
                if len(surface.angles) == 3:
                    # The underlying polygon() is deterministic. Therefore, we
                    # do not need any special checks for triangles.
                    pass
                else:
                    # For higher ngons, we cannot decide yet whether they are
                    # the same without actually instantiating them which is
                    # extremely costly and also tends to lead to memory leaks
                    # in the scheduler.
                    raise NotImplementedError("exact filtering is not supported yet")

            return True

        return predicate

    @cached_method
    def polygon(self):
        r"""
        Return an actual n-gon with concrete lengths selected.

        EXAMPLES::

            >>> Ngon((1, 1, 1)).polygon()
            Polygon(vertices=[(0, 0), (2, 0), (1, c)])

        """
        from flatsurf import EuclideanPolygonsWithAngles

        E = EuclideanPolygonsWithAngles(*self.angles)

        P = E.random_element()

        # A random element can be very small or very big. This tricks some of
        # the heuristics here (ideally it shouldn't matter and all heuristics
        # should just scale with the polygon area.)
        # Anyway, we rescale the polygon; in particular this takes the
        # randomness out of triangles which helps with making doctests fully
        # reproducible in this project.

        assert P.vertex(0)[0] == 0 and P.vertex(0)[1] == 0 and P.vertex(1)[1] == 0

        P = ~P.vertex(1)[0] * P

        while P.area() > 2:
            from sage.all import QQ

            P = ~QQ(2) * P
        while 2 * P.area() < 1:
            P = 2 * P

        return P

    @cached_method
    def _surface(self):
        r"""
        Return a sage-flatsurf surface that realizes the unfolding of this
        n-gon.

        EXAMPLES::

            >>> Ngon((1, 1, 1)).surface()
            Translation Surface in H_1(0) built from 2 equilateral triangles

        """
        from flatsurf import similarity_surfaces

        from flatsurvey.survey import IS_SURVEY_ORCHESTRATOR

        assert (
            not IS_SURVEY_ORCHESTRATOR
        ), "sage-flatsurf surfaces should not be instantiated in the survey scheduler since they and their attached SageMath and C++ objects tend to cause memory leaks"

        S = similarity_surfaces.billiard(self.polygon())
        S = S.minimal_cover(cover_type="translation")
        return S

    def __reduce__(self):
        r"""
        Rewrite this surface in a form that can be easily turned into a compact
        pickle.

        EXAMPLES::

            >>> from pickle import dumps, loads
            >>> surface = Ngon((1, 1, 1))
            >>> loads(dumps(surface)) == surface
            True

        """
        return (Ngon, (self.angles, self.polygon.cache))  # type: ignore

    def __hash__(self):
        if self.polygon.cache is None:  # type: ignore
            raise Exception(
                "cannot hash Ngon whose polygon() has not been determined yet"
            )

        return hash((tuple(self.angles), self.polygon()))

    def __eq__(self, other):
        return (
            isinstance(other, Ngon)
            and self.angles == other.angles
            and self.polygon.cache == other.polygon.cache  # type: ignore
        )

    @staticmethod
    @click.command(
        name="ngon",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--angle",
        "-a",
        multiple=True,
        type=int,
        help="inner angles of the polygon in multiples of (N - 2)π/A where N is the number of vertices and A the sum of all provided angles",
    )
    @Bindings.click
    def click(bindings: Bindings, angle):
        r"""
        Parse command line options to configure an n-gon into the ``bindings``.

        EXAMPLES::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Ngon.click, "--angle", "1", "--angle", "2", "--angle", "3")

        """
        bindings.define(Surface, Ngon)
        with bindings.scope(Ngon) as scoped:
            scoped.define(angles=angle)

    @staticmethod
    def create(bindings: Bindings) -> "Ngon":
        r"""
        Return an ``Ngon`` instance from the configuration registered in
        ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> Ngon.create(bindings)
            Ngon([1, 1, 1])

        """
        with bindings.scope(Ngon) as scoped:
            return Ngon(angles=scoped.get("angles"))


class Ngons:
    r"""
    The translation surfaces that come from unfolding n-gons.

    EXAMPLES::

        >>> from flatsurvey.pipeline.bindings import Bindings
        >>> ngons = Ngons(vertices=3, min=0, limit=None, count=6, literature="include", family=None, filter=None)
        >>> list(ngons)
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> bindings = Bindings()
        >>> ngons = Ngons(vertices=3, min=0, limit=None, count=6, literature='include', family=None, filter=None)
        >>> list(ngons)
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> ngons = Ngons(vertices=3, min=0, limit=None, count=3, literature='include', family=None, filter='lambda a, b, c: (a + b + c) % 2 == 0')
        >>> list(ngons)
        [Ngon([1, 1, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        >>> ngons = Ngons(vertices=3, min=0, limit=None, count=3, literature='include', family='(1, 1, n)', filter=None)
        >>> list(ngons)
        [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3])]

        >>> ngons = Ngons(vertices=3, min=0, limit=None, count=3, literature='include', family='[(1, 1, n), (1, 2, 12*n)]', filter=None)
        >>> list(ngons)
        [Ngon([1, 1, 1]), Ngon([1, 2, 12]), Ngon([1, 1, 2])]

    """

    def __init__(self, vertices, min, limit, count, literature, family, filter):
        self._vertices = vertices
        self._min = min
        self._limit = limit
        self._count = count
        self._literature = literature
        self._family = family
        self._filter = filter

    def __iter__(self):
        r"""
        Return an iterator over this family of n-gons.

        EXAMPLES::

            >>> from flatsurvey.pipeline.bindings import Bindings
            >>> ngons = Ngons(vertices=3, min=0, limit=None, count=6, literature="include", family=None, filter=None)
            >>> list(ngons)
            [Ngon([1, 1, 1]), Ngon([1, 1, 2]), Ngon([1, 1, 3]), Ngon([1, 2, 2]), Ngon([1, 1, 4]), Ngon([1, 2, 3])]

        """
        count = self._count

        filter = self._filter
        if filter is not None:
            if not callable(filter):
                filter = eval(filter, {})

        import itertools

        for n in itertools.count(start=self._min):
            if self._limit is not None and n > self._limit:
                break

            if self._family:
                pool = eval(self._family, {"n": n})
                if not isinstance(pool, list):
                    pool = [pool]
            else:
                total_angle = n
                pool = partitions(total_angle, self._vertices)

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

                ngon = Ngon(angles)

                if self._literature == "include":
                    pass
                elif self._literature == "exclude":
                    if ngon.reference():
                        continue
                elif self._literature == "only":
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

    @staticmethod
    @click.command(
        name="ngons",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--vertices", "-n", type=int, required=True, help="number of vertices"
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
    @Bindings.click
    def click(
        bindings: Bindings, vertices, min, limit, count, literature, family, filter
    ):
        r"""
        Parse command line options to configure a family of n-gons into the ``bindings``.

        EXAMPLES::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Ngons.click, "--vertices", "3")

        """
        bindings.survey(
            Surface,
            Ngons(
                vertices=vertices,
                min=min,
                limit=limit,
                count=count,
                literature=literature,
                family=family,
                filter=filter,
            ),
        )


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
    # doctests of Ngon.click do not run unless explicitly mentioned here due to the click decorator.
    "Ngon.click": Ngon.click.__doc__,
    # doctests of Ngons.click do not run unless explicitly mentioned here due to the click decorator.
    "Ngons.click": Ngons.click.__doc__,
}
