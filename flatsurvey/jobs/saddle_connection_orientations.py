r"""
The saddle connection directions on a translation surface module scaling.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "saddle-connection-orientations", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker saddle-connection-orientations [OPTIONS]
      Orientations of saddle connections on the surface, i.e., the vectors of
      saddle connections irrespective of scaling and sign.
    Options:
      --help  Show this message and exit.

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

import click

from flatsurvey.jobs.saddle_connections import SaddleConnections
from flatsurvey.pipeline import Bindings, Processor
from flatsurvey.reporting import Report
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class SaddleConnectionOrientations(Processor, Command):
    r"""
    Orientations of saddle connections on the surface, i.e., the vectors of
    saddle connections irrespective of scaling and sign.
    """

    def __init__(
        self, saddle_connections: SaddleConnections, report: Report | None = None
    ):
        super().__init__(producers=[saddle_connections], report=report)

        self._saddle_connections = saddle_connections

        self._seen = None
        self._backlog = []

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``SaddleConnectionOrientations`` instance from the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnectionOrientations.click, bindings=bindings)
            >>> SaddleConnectionOrientations.create(bindings)
            saddle-connection-orientations

        """
        return SaddleConnectionOrientations(
            saddle_connections=bindings.get(SaddleConnections),
            report=bindings.get(Report),
        )

    @staticmethod
    @click.command(
        name="saddle-connection-orientations",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @Bindings.click
    def click(bindings: Bindings):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(SaddleConnectionOrientations.click)

        """
        del bindings

    def promote_symmetries(self):
        r"""
        Produce all the directions next that are obtained by symmetry of the
        underlying surface from the current direction.

        Note that each direction is still only reported once.

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnectionOrientations.click, bindings=bindings)
            >>> sco = SaddleConnectionOrientations.create(bindings)

        Normally, we produce directions coming from saddle connections in one
        sector by length::

            >>> import asyncio
            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (0, (2*c ~ 3.4641016))

            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (3, (c ~ 1.7320508))

            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (3, (3*c ~ 5.1961524))

        However, we can request the symmetric directions of the last one next::

            >>> sco.promote_symmetries()
            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (6, 0)

        Afterwards, it goes back to the normal iteration from before automatically::

            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (-3, (5*c ~ 8.6602540))

        """
        for Q in self._saddle_connections._surface.symmetries:
            if Q.is_one():
                continue
            if Q[0][1] < 0:
                continue  # ignore negative pair of each rotation

            from flatsurf.geometry.pyflatsurf.conversion import VectorSpaceConversion

            conversion = VectorSpaceConversion.from_pyflatsurf_from_elements(
                [self._current]
            )

            self._backlog.append(conversion(Q * conversion.section(self._current)))

    def demote_symmetries(self):
        r"""
        Request that not as many directions that are obtained as symmetries of
        the current direction are produced.

        This method can be called after a call to :meth:`promote_symmetries` to
        not produce all symmetries but only half of them.

        It can be called multiple times to produce even less.

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnectionOrientations.click, bindings=bindings)
            >>> sco = SaddleConnectionOrientations.create(bindings)

        We ask for some symmetric directions but immediately cancel the request
        and get the sequence of directions without symmetries::

            >>> import asyncio
            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (0, (2*c ~ 3.4641016))

            >>> sco.promote_symmetries()
            >>> sco.demote_symmetries()

            >>> import asyncio
            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'
            >>> sco._current
            (3, (c ~ 1.7320508))

        """
        # The "1" in the below formula is a bit random and probably makes not
        # much of a difference. We try to get a bit away from the initial
        # sector with this.
        self._backlog = self._backlog[1::2]

    async def _process(self, direction, cost):
        import cppyy

        vector = type(direction)(direction)
        if self._seen == None:
            self._seen = cppyy.gbl.std.set[type(vector), type(vector).CompareSlope]()

        if vector.x():
            try:
                vector = type(vector)(vector.x() / vector.x(), vector.y() / vector.x())
            except Exception:
                pass
        if vector.y():
            try:
                vector = type(vector)(vector.x() / vector.y(), vector.y() / vector.y())
            except Exception:
                pass

        if self._seen.find(vector) == self._seen.end():
            self._seen.insert(vector)
            self._current = direction
            self._current = type(self._current)(self._current)

            await self._report.result(self, self._current)

            await self._notify_consumers(cost)

        return "NOT_COMPLETED"

    async def _consume(self, product, cost):
        r"""
        Turn a saddle connection into its orientation.

        EXAMPLES::

            >>> import asyncio
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> sco = SaddleConnectionOrientations(saddle_connections=SaddleConnections(surface))

            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'

        Check that the JSON output works::

            >>> from flatsurvey.reporting import Json

            >>> report = Report([Json({Surface: surface}, output="-")], ignore=["saddle-connections"])
            >>> sco = SaddleConnectionOrientations(saddle_connections=SaddleConnections(surface), report=report)

            >>> asyncio.run(sco.produce())
            'NOT_EXHAUSTED'

            >>> report.flush()
            {"surface": {...}, "saddle-connection-orientations": [{"timestamp": "...", "value": {"type": "Vector<eantic::renf_elem_class>", ...}}]}

        """
        while self._backlog:
            await self._process(self._backlog.pop(), 0)

        return await self._process(product.vector(), cost)
