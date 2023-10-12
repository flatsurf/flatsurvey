r"""
Directions in $S^1(2d')$.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "boshernitzan-conjecture-orientations", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker boshernitzan-conjecture-orientations [OPTIONS]
      Produces directions in $S^1(2d')$, i.e., corresponding to certain roots of unity, as used in Conjecture 2.2 of Boshernitzan's *Billiards and Rational Periodic Directions in Polygons*.
    Options:
      --help  Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline import Producer
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


class BoshernitzanConjectureOrientations(Producer, Command):
    r"""
    Produces directions in $S^1(2d')$, i.e., corresponding to certain roots
    of unity, as used in Conjecture 2.2 of Boshernitzan's *Billiards and
    Rational Periodic Directions in Polygons*.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> BoshernitzanConjectureOrientations(surface=surface)
        boshernitzan-conjecture-orientations

    TESTS::

        >>> BoshernitzanConjectureOrientations(surface=Ngon((1, 1, 2)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((1, 1, 3)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((1, 2, 2)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((1, 2, 3)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((1, 3, 3)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((2, 2, 3)))
        boshernitzan-conjecture-orientations
        >>> BoshernitzanConjectureOrientations(surface=Ngon((2, 3, 3)))
        boshernitzan-conjecture-orientations

    """

    @copy_args_to_internal_fields
    def __init__(self, surface):
        super().__init__()

        angles = surface.angles

        if len(angles) != 3:
            raise NotImplementedError(
                "Special directions for Boshernitzan Conjecture only implemented for triangles"
            )

        self._producer = None

    @property
    def assertions(self):
        r"""
        The parts of Boshernitzan's conjecture to which this surface applies.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
            >>> BoshernitzanConjectureOrientations(Ngon((1, 1, 1))).assertions
            ['b', 'c']

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((1, 1, 2))).assertions
            ['a', 'c', 'e']

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 6))).assertions
            ['b']

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 33))).assertions
            ['a']

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 34))).assertions
            ['b']

        """
        a, b, c = sorted(self._surface.angles)
        d = a + b + c

        assertions = []

        if d % 2 == 0:
            assertions.append("a")
        else:
            assertions.append("b")

        if d <= 12 and (a, b, c) != (2, 3, 6):
            assertions.append("c")

        if c == a + b:
            assertions.append("e")

        return assertions

    @property
    def _directions(self):
        r"""
        Return the directions in $S^1(2d')$.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
            >>> BoshernitzanConjectureOrientations(Ngon((1, 1, 1)))._directions
            [(4, 0), (0, 4)]

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((1, 1, 2)))._directions
            [(0, 2), (1, -1)]

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 6)))._directions
            [(0, 32)]

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 33)))._directions
            [(0, 256), (-128*c^17 + 2176*c^15 - 15360*c^13 + 58368*c^11 - 129280*c^9 + 167936*c^7 - 120192*c^5 + 39040*c^3 - 2688*c, -128*c^14 + 2048*c^12 - 13184*c^10 + 43520*c^8 - 77568*c^6 + 71552*c^4 - 28800*c^2 + 2432)]

        ::

            >>> BoshernitzanConjectureOrientations(Ngon((2, 3, 34)))._directions
            [(0, 256)]

        """
        directions = []

        a, b, c = self._surface.angles
        d = a + b + c

        from sage.all import vector

        edges = self._surface.polygon().edges()

        if d % 2 == 0:
            # Modulo symmetries in the unfolding, there are only two
            # directions in S¹(2d')=S¹(2d).
            edge = edges[0]
            directions.append(vector((-edge[1], edge[0])))

            edge = edges[2] if a % 2 == 1 else edges[1]
            directions.append(vector((-edge[1], edge[0])))
        else:
            # Modulo symmetries in the unfolding, there are two directions in
            # S¹(2d')=S¹(4d).
            edge = edges[0]

            if "c" in self.assertions:
                # The direction parallel to the first edge is also in S¹(d')
                # and so relevant for part (c) of the conjecture.
                directions.append(edge)

            # The direction orthogonal to the first edge is in S¹(2d') but not
            # in S¹(d') and thus relevant to part (b) and (c) of the
            # conjecture.
            directions.append(vector((-edge[1], edge[0])))

        symmetries = list(self._surface.unfolding_symmetries)
        for symmetry in list(symmetries):
            symmetries.append(-symmetry)
        for symmetry in list(symmetries):
            symmetries.append(~symmetry)
        for symmetry in symmetries:
            symmetry.set_immutable()
        symmetries = set(symmetries)

        # Assert that the directions are in S¹(2d')
        for z in directions:
            from sage.all import lcm

            v = self._pow(z, 2 * lcm(2, d))

            assert (
                v[0] > 0 and v[1] == 0
            ), f"{z} is not in S¹(2d') for angles {a, b, c} since {v} != (1, 0)"

        # Assert that the directions span S¹(2d')
        directions_with_symmetries = list(
            symmetry * direction for direction in directions for symmetry in symmetries
        )
        for direction in directions_with_symmetries:
            direction.set_immutable()

        directions_with_symmetries = set(directions_with_symmetries)

        if d % 2 == 0 or "c" in self.assertions:
            assert len(directions_with_symmetries) == 2 * lcm(
                2, d
            ), f"{directions} does not generate the expected subset of S¹(2d'). Expected that this generated {2*lcm(2, d)} directions but it generates {len(directions_with_symmetries)}, namely {directions_with_symmetries}"
        else:
            relevant_directions = [
                v for v in directions_with_symmetries if self._pow(v, lcm(2, d))[0] < 0
            ]
            assert len(relevant_directions) >= lcm(
                2, d
            ), f"{directions} does not generate the expected subset of S¹(2d'). Expected that this generated S¹(2d')\\S¹(d') but it generates {len(directions_with_symmetries)}, namely {directions_with_symmetries}"

        # Assert that the directions are independent modulo symmetries of the triangle.
        for direction in directions:
            for symmetry in symmetries:
                image = symmetry * direction
                if image == direction:
                    continue
                assert (
                    symmetry * direction not in directions
                ), f"directions {direction} and {symmetry * direction} from {directions} must be independent generators in S¹(2d') with angles {a, b, c} but they are connected by {symmetry} which is one of the {len(symmetries)} unfolding symmetries"

        return directions

    @classmethod
    def _pow(self, z, n):
        from sage.all import vector

        def mul(a, b):
            return vector((a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]))

        if n == 0:
            return vector(z.base_ring(), (1, 0))
        elif n < 0:
            raise NotImplementedError("power with negative exponent not implemented yet")
        elif n % 2 == 0:
            return self._pow(mul(z, z), n // 2)
        else:
            return mul(self._pow(z, n - 1), z)

    def _produce(self):
        r"""
        Produces the special directions to verify (a), (b), (c), (e) of
        Boshernitzan's conjecture.

        EXAMPLES:

        For the (1, 1, 1) triangle, the conjecture (c) makes a statement about
        12 directions. Since there are three rotational symmetries and we can
        ignore signs, we only have to check two directions::

            >>> import asyncio
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (4, 0)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 4)

            >>> asyncio.run(orientations.produce())
            False

        For the (1, 1, 2) triangle, the conjectures make a statement about 8
        directions. There are four rotation symmetries (including taking the
        negative of a direction) so we need to check two different directions::
        ::

            >>> surface = Ngon((1, 1, 2))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 2)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (1, -1)

            >>> asyncio.run(orientations.produce())
            False

        ::

            >>> surface = Ngon((1, 2, 3))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 8)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (2*c, -6)

            >>> asyncio.run(orientations.produce())
            False

        ::

            >>> surface = Ngon((2, 3, 3))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 2)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (-c0, c0 - 2)

            >>> asyncio.run(orientations.produce())
            False

        """
        if self._producer is None:
            self._producer = iter(self._directions)

        try:
            self._current = next(self._producer)
            return not Producer.EXHAUSTED
        except StopIteration:
            return Producer.EXHAUSTED

    @classmethod
    @click.command(
        name="boshernitzan-conjecture-orientations",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES")[0],
    )
    def click():
        return {
            "bindings": [
                PartialBindingSpec(
                    BoshernitzanConjectureOrientations,
                    name="saddle_connection_orientations",
                )()
            ]
        }

    def command(self):
        return ["boshernitzan-conjecture-orientations"]
