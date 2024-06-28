r"""
Determines whether a surface decomposes completely into cylinders in some direction.

Naturally, this can only be decided partially, i.e., we can say, "yes", there
is such a direction but we can never say "no" _all_ directions have a
non-cylinder.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "cylinder-periodic-direction", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker cylinder-periodic-direction [OPTIONS]
      Determines whether there is a direction for which the surface decomposes
      into cylinders.
    Options:
      --limit INTEGER  stop search after having looked at that many flow
                       decompositions  [default: no limit]
      --cache-only     Do not perform any computation. Only query the cache.
      --help           Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2022 Julian Rüth
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

from flatsurvey.command import Command
from flatsurvey.pipeline import Goal
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand


class CylinderPeriodicDirection(Goal, Command):
    r"""
    Determines whether there is a direction for which the surface decomposes
    into cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
        >>> CylinderPeriodicDirection(report=None, flow_decompositions=flow_decompositions, cache=None)
        cylinder-periodic-direction

    """
    DEFAULT_LIMIT = None

    @copy_args_to_internal_fields
    def __init__(
        self,
        report,
        flow_decompositions,
        cache,
        cache_only=Goal.DEFAULT_CACHE_ONLY,
        limit=DEFAULT_LIMIT,
    ):
        super().__init__(
            producers=[flow_decompositions],
            report=report,
            cache=cache,
            cache_only=cache_only,
        )

        self._directions = 0

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = CylinderPeriodicDirection(report=None, flow_decompositions=flow_decompositions, cache=None)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from io import StringIO
            >>> cache = Cache(jsons=[StringIO(
            ... '''{"cylinder-periodic-direction": [{
            ...   "surface": {
            ...     "type": "Ngon",
            ...     "angles": [1, 1, 1]
            ...   },
            ...   "result": null
            ... }, {
            ...   "surface": {
            ...     "type": "Ngon",
            ...     "angles": [1, 1, 1]
            ...   },
            ...   "result": true
            ... }]}''')], pickles=None, report=None)
            >>> goal = CylinderPeriodicDirection(report=None, flow_decompositions=flow_decompositions, cache=cache)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        TESTS:

        Check that the JSON output for this goal works::

            >>> from flatsurvey.reporting import Json, Report

            >>> report = Report([Json(surface)])
            >>> goal = CylinderPeriodicDirection(report=report, flow_decompositions=flow_decompositions, cache=cache)

            >>> import asyncio
            >>> asyncio.run(goal.consume_cache())
            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "cylinder-periodic-direction": [{"timestamp": ..., "cached": true, "value": true}]}

        """
        results = self._cache.get(
            self,
            self._flow_decompositions._surface.cache_predicate(
                False, cache=self._cache
            ),
        )

        verdict = self.reduce(results)

        if verdict is not None or self._cache_only:
            await self._report.result(self, verdict, cached=True)
            self._resolved = Goal.COMPLETED

    @classmethod
    def reduce(cls, results):
        r"""
        Merge results of various runs into a final verdict.

        EXAMPLES::

            >>> from collections import namedtuple
            >>> Result = namedtuple("Result", "result")
            >>> CylinderPeriodicDirection.reduce([Result(None), Result(None)])
            >>> CylinderPeriodicDirection.reduce([Result(True), Result(None)])
            True

        """
        results = [result.result for result in results]

        assert not any([result is False for result in results])
        return True if any(result for result in results) else None

    @classmethod
    @click.command(
        name="cylinder-periodic-direction",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="stop search after having looked at that many flow decompositions  [default: no limit]",
    )
    @Goal._cache_only_option
    def click(limit, cache_only):
        return {
            "bindings": [
                PartialBindingSpec(CylinderPeriodicDirection)(
                    limit=limit, cache_only=cache_only
                )
            ],
            "goals": [CylinderPeriodicDirection],
        }

    async def _consume(self, decomposition, cost):
        r"""
        Determine wheter ``decomposition`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
            >>> cpd = CylinderPeriodicDirection(report=Report([log]), flow_decompositions=flow_decompositions, cache=None)

        Investigate in a single direction. We find that this direction is
        cylinder periodic::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            [Ngon([1, 1, 1])] [CylinderPeriodicDirection] True (directions: 1)
            True

        TESTS:

        Verify that the JSON output works::

            >>> from flatsurvey.reporting import Json, Report

            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
            >>> report = Report([Json(surface)])
            >>> cpd = CylinderPeriodicDirection(report=report, flow_decompositions=flow_decompositions, cache=None)

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            True

            >>> asyncio.run(cpd.report())
            >>> report.flush()
            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "cylinder-periodic-direction": [{"timestamp": ..., "directions": 1, "value": true}]}


        """
        self._directions += 1

        if all([component.cylinder() for component in decomposition.components()]):
            await self.report(True, decomposition=decomposition)
            return Goal.COMPLETED

        if self._limit is not None and self._directions >= self._limit:
            await self.report()
            return Goal.COMPLETED

        return not Goal.COMPLETED

    async def report(self, result=None, **kwargs):
        if self._resolved != Goal.COMPLETED:
            await self._report.result(self, result, directions=self._directions)
