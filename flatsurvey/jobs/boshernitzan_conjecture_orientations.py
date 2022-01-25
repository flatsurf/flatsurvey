r"""
Special directions in triangles.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "boshernitzan-conjecture-orientations", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker boshernitzan-conjecture-orientations [OPTIONS]
      Produces some particular directions in triangles related to a conjecture of
      Boshernitzan.
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
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.pipeline.util import PartialBindingSpec

class BoshernitzanConjectureOrientations(Producer):
    r"""
    Produces some particular directions in triangles related to
    a conjecture of Boshernitzan.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> BoshernitzanConjectureOrientations(surface=surface)
        boshernitzan-conjecture-orientations

    """
    @copy_args_to_internal_fields
    def __init__(self, surface):
        super().__init__()

        angles = surface.angles

        if len(angles) != 3:
            raise NotImplementedError("Special directions for Boshernitzan Conjecture only implemented for triangles")

        a, b, c = angles

        from sage.all import vector
        orthogonals = [vector((-e[1], e[0])) for e in surface.polygon().edges()]

        if sum(angles) % 2 == 0:
            if a % 2 == b % 2:
                self._orientations = [orthogonals[1], orthogonals[0]]
            elif a % 2 == c % 2:
                self._orientations = [orthogonals[2], orthogonals[1]]
            elif b % 2 == c % 2:
                self._orientations = [orthogonals[0], orthogonals[2]]
        else:
            self._orientations = [orthogonals[0]]

    def _produce(self):
        r"""
        Produces one or two special directions, depending on
        the parity of the angles of the triangle.

        EXAMPLES::

            >>> import asyncio
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import BoshernitzanConjectureOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 4)

            >>> asyncio.run(orientations.produce())
            False

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
            (-1, -1)

            >>> asyncio.run(orientations.produce())
            False

        ::

            >>> surface = Ngon((1, 2, 3))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (-(2*c ~ 3.4641016), -2)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            ((2*c ~ 3.4641016), -6)

            >>> asyncio.run(orientations.produce())
            False

        ::

            >>> surface = Ngon((2, 3, 3))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            ((c0 ~ 1.4142136), -(c0 ~ 1.4142136))

            >>> asyncio.run(orientations.produce())
            True
            >>> orientations._current
            (0, 2)

            >>> asyncio.run(orientations.produce())
            False

        """
        if self._orientations:
            self._current = self._orientations.pop()
            return not Producer.EXHAUSTED

        return Producer.EXHAUSTED

    @classmethod
    @click.command(
        name="boshernitzan-conjecture-orientations",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES")[0],
    )
    def click():
        return {"bindings": [
            PartialBindingSpec(BoshernitzanConjectureOrientations, name="saddle_connection_orientations")()
        ]}

    def command(self):
        return ["boshernitzan-conjecture-orientations"]
