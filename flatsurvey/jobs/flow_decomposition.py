r"""
Computes flow decompositions of a flat triangulation into cylinders and minimal components.

Usually you do not need to interact with this module directly. Flow
decompositions are created by the bits of the computation that need them on
demand.

However, you can still change some of the behaviour of this module through the
`flow-decompositions` command, e.g., to set a different `--limit` for the
number of Zorich induction steps:

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "flow-decompositions", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker flow-decompositions [OPTIONS]
      Turns directions coming from saddle connections into flow decompositions.
    Options:
      --limit INTEGER  Zorich induction steps to perform before giving up  [default: 256]
      --help           Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2021 Julian Rüth
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
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand

from flatsurvey.pipeline import Processor
from flatsurvey.command import Command


class FlowDecompositions(Processor, Command):
    r"""
    Turns directions coming from saddle connections into flow decompositions.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
        flow-decompositions

    """
    DEFAULT_LIMIT = 256

    @copy_args_to_internal_fields
    def __init__(
        self, surface, saddle_connection_orientations, report=None, limit=DEFAULT_LIMIT
    ):
        super().__init__(producers=[saddle_connection_orientations], report=report)

    @classmethod
    @click.command(
        name="flow-decompositions",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES:")[0],
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        show_default=True,
        help="Zorich induction steps to perform before giving up",
    )
    def click(limit):
        return {
            "bindings": [PartialBindingSpec(FlowDecompositions)(limit=limit)],
        }

    def command(self):
        command = ["flow-decompositions"]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        return command

    async def _consume(self, orientation, cost):
        r"""
        Produce the flow decomposition corresponding to ``orientation``.

        EXAMPLES::

            >>> import asyncio
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> decompositions = FlowDecompositions(surface=surface, report=Report([Log(surface)]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
            >>> produce = decompositions.produce() # indirect doctest
            >>> asyncio.run(produce)  # doctest: +ELLIPSIS
            [Ngon([1, 1, 1])] [FlowDecompositions] ¯\_(ツ)_/¯ (orientation: (0, ...)) (cylinders: 1) (minimal: 0) (undetermined: 0)
            True
            >>> decompositions._current
            FlowDecomposition with 1 cylinders, 0 minimal components and 0 undetermined components

        TESTS:

        Check that the JSON output works::

            >>> from flatsurvey.reporting import Json

            >>> report = Report([Json(surface)])
            >>> decompositions = FlowDecompositions(surface=surface, report=report, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))

            >>> asyncio.run(decompositions.produce())
            True

            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "flow-decompositions": [{"timestamp": ..., "orientation": {"type": "Vector<eantic::renf_elem_class>", "pickle": "..."}, "cylinders": 1, "minimal": 0, "undetermined": 0, "value": null}]}

        """
        start = time.perf_counter()
        self._current = self._surface.orbit_closure().decomposition(
            orientation, self._limit
        )
        cost += time.perf_counter() - start

        await self._report.result(
            self,
            # flatsurf::FlowDecomposition cannot be serialized yet: https://github.com/flatsurf/flatsurf/issues/274
            # self._current,
            None,
            orientation=orientation,
            cylinders=len(self._current.cylinders()),
            minimal=len(self._current.minimalComponents()),
            undetermined=len(self._current.undeterminedComponents()),
        )

        await self._notify_consumers(cost)

        return not Processor.EXHAUSTED
