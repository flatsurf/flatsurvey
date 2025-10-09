r"""
Computes flow decompositions of a flat triangulation into cylinders and minimal components.

Usually you do not need to interact with this module directly. Flow
decompositions are created by the bits of the computation that need them on
demand.

However, you can still change some of the behaviour of this module through the
`flow-decompositions` command, e.g., to set a different `--limit` for the
number of Zorich induction steps:

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "flow-decompositions", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker flow-decompositions [OPTIONS]
      Turns directions coming from saddle connections into flow decompositions.
    Options:
      --limit INTEGER  Zorich induction steps to perform before giving up  [default: 64]
      --help           Show this message and exit.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
#
#  Flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
# *********************************************************************

import time

import click

from flatsurvey.jobs.saddle_connection_orientations import SaddleConnectionOrientations
from flatsurvey.pipeline import Bindings, Processor
from flatsurvey.reporting.report import Report
from flatsurvey.surfaces import Surface
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class FlowDecompositions(Processor, Command):
    r"""
    Turns directions coming from saddle connections into flow decompositions.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        flow-decompositions

    """

    DEFAULT_LIMIT = 64

    def __init__(
        self,
        surface: Surface,
        saddle_connection_orientations: SaddleConnectionOrientations,
        report: Report | None = None,
        limit=DEFAULT_LIMIT,
    ):
        super().__init__(producers=[saddle_connection_orientations], report=report)

        self._surface = surface
        self._limit = limit

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``FlowDecompositions`` instance from the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(FlowDecompositions.click, bindings=bindings)
            >>> FlowDecompositions.create(bindings)
            flow-decompositions

        """
        with bindings.scope(FlowDecompositions) as scoped:
            return FlowDecompositions(
                surface=bindings.get(Surface),
                saddle_connection_orientations=bindings.get(
                    SaddleConnectionOrientations
                ),
                report=bindings.get(Report),
                limit=scoped.get("limit", default=FlowDecompositions.DEFAULT_LIMIT),
            )

    @staticmethod
    @click.command(
        name="flow-decompositions",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES:")[0],  # type: ignore
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        show_default=True,
        help="Zorich induction steps to perform before giving up",
    )
    @Bindings.click
    def click(bindings: Bindings, limit):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(FlowDecompositions.click)

        """
        with bindings.scope(FlowDecompositions) as scoped:
            scoped.define(limit=limit)

    async def _consume(self, product, cost):
        r"""
        Produce the flow decomposition corresponding to ``orientation``.

        EXAMPLES::

            >>> import asyncio
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> decompositions = FlowDecompositions(surface=surface, report=Report([Log(surface)]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> produce = decompositions.produce() # indirect doctest
            >>> asyncio.run(produce)  # doctest: +ELLIPSIS
            'NOT_EXHAUSTED'
            >>> decompositions._current
            FlowDecomposition with 1 cylinders, 0 minimal components and 0 undetermined components

        TESTS:

        Check that the JSON output works::

            >>> from flatsurvey.reporting import Json

            >>> report = Report([Json({Surface: surface}, output="-")], ignore=["saddle-connections"])
            >>> decompositions = FlowDecompositions(surface=surface, report=report, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

            >>> asyncio.run(decompositions.produce())
            'NOT_EXHAUSTED'

            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "flow-decompositions": [{"timestamp": "...", "orientation": {"type": "Vector<eantic::renf_elem_class>", "repr": "..."}, "cylinders": 1, "minimal": 0, "undetermined": 0, "value": null}]}


        """
        from flatsurvey.survey import IS_SURVEY_ORCHESTRATOR

        assert (
            not IS_SURVEY_ORCHESTRATOR
        ), "pyflatsurf objects should not be instantiated in the survey scheduler since they tend to cause memory leaks"

        start = time.perf_counter()

        from flatsurf import GL2ROrbitClosure

        self._current = GL2ROrbitClosure(self._surface.surface()).decomposition(
            product, self._limit
        )
        cost += time.perf_counter() - start

        await self._report.result(
            self,
            # flatsurf::FlowDecomposition cannot be serialized yet: https://github.com/flatsurf/flatsurf/issues/274
            # self._current,
            None,
            orientation=product,
            cylinders=len(self._current.cylinders()),
            minimal=len(self._current.minimalComponents()),
            undetermined=len(self._current.undeterminedComponents()),
        )

        await self._notify_consumers(cost)

        return "NOT_COMPLETED"


__test__ = {
    # doctests of click do not run unless explicitly mentioned here due to the click decorator.
    "FlowDecompositions.click": FlowDecompositions.click.__doc__,
}
