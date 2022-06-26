r"""
Determines whether a surface decomposes completely into cylinders in all directions.

Naturally, this can only be decided partially, i.e., we can say, "no",
there is some direction with a minimal component but we can never say "yes",
_all_ directions are cylinder periodic.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "completely-cylinder-periodic", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker completely-cylinder-periodic [OPTIONS]
      Determines whether for all directions given by saddle connections, the
      decomposition of the surface is completely cylinder periodic, i.e., the
      decomposition consists only of cylinders.
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

from flatsurvey.pipeline import Goal
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


class CompletelyCylinderPeriodic(Goal, Command):
    r"""
    Determines whether for all directions given by saddle connections, the
    decomposition of the surface is completely cylinder periodic, i.e., the
    decomposition consists only of cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CompletelyCylinderPeriodic(report=None, flow_decompositions=flow_decompositions, cache=None)
        completely-cylinder-periodic

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
            producers=[flow_decompositions], report=report, cache=cache, cache_only=cache_only
        )

        self._undetermined_directions = 0
        self._cylinder_periodic_directions = 0

    @classmethod
    @click.command(
        name="completely-cylinder-periodic",
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
                PartialBindingSpec(CompletelyCylinderPeriodic)(
                    limit=limit, cache_only=cache_only
                )
            ],
            "goals": [CompletelyCylinderPeriodic],
        }

    def command(self):
        command = ["completely-cylinder-periodic"]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        if self._cache_only != self.DEFAULT_CACHE_ONLY:
            command.append("--cache-only")
        return command

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

            >>> make_goal = lambda cache, report: CompletelyCylinderPeriodic(report=report, flow_decompositions=flow_decompositions, cache=cache)

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = make_goal(None, None)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from flatsurvey.reporting import Report, Json
            >>> log = Report([Json(surface)])

            >>> from io import StringIO
            >>> goal = make_goal(Cache(jsons=[StringIO(
            ... '''{"completely-cylinder-periodic": [{
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
            ...   "result": false
            ... }]}''')], pickles=None, report=None), log)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        The cached verdict can be reported back in JSON format::

            >>> log.flush()
            {"surface": {...}, "completely-cylinder-periodic": [{"cached": true, "value": false}]}

        """
        results = self._cache.get(self, self._flow_decompositions._surface.cache_predicate(False, cache=self._cache))

        verdict = self.reduce(results)

        if verdict is not None or self._cache_only:
            await self._report.result(self, verdict, cached=True)
            self._resolved = Goal.COMPLETED

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return a final verdict.

        EXAMPLES::

            >>> from collections import namedtuple
            >>> Result = namedtuple("Result", "result")
            >>> CompletelyCylinderPeriodic.reduce([Result(None), Result(None)])
            >>> CompletelyCylinderPeriodic.reduce([Result(None), Result(False)])
            False

        """
        results = [result.result for result in results]

        assert not any(results)
        return False if any(result is False for result in results) else None

    async def _consume(self, decomposition, cost):
        r"""
        Determine wheter ``decomposition`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=Report([log]), flow_decompositions=flow_decompositions, cache=None)

        Investigate in a single direction::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            True

        Since we have not found any direction that is not cylinder periodic
        (since there are none), we cannot tell whether the surface is
        completely cylinder periodic::

            >>> report = ccp.report()
            >>> asyncio.run(report)
            [Ngon([1, 1, 1])] [CompletelyCylinderPeriodic] ¯\_(ツ)_/¯ (cylinder_periodic_directions: 1) (undetermined_directions: 0)

        """
        if decomposition.minimalComponents():
            await self.report(False, decomposition=decomposition)
            return Goal.COMPLETED

        if all([component.cylinder() for component in decomposition.components()]):
            self._cylinder_periodic_directions += 1
            if (
                self._limit is not None
                and self._cylinder_periodic_directions >= self._limit
            ):
                self.report()
                return Goal.COMPLETED

        if decomposition.undeterminedComponents():
            self._undetermined_directions += 1

        return not Goal.COMPLETED

    async def report(self, result=None, **kwargs):
        r"""
        Report whether this surface is completely cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Json, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 11))
            >>> report = Report([Json(surface)])
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=report, flow_decompositions=flow_decompositions, cache=None)

        Report that we found a direction that is not a cylinder::

            >>> import asyncio
            >>> asyncio.run(ccp.report(result=False))

            >>> report.flush()
            {"surface": {...}, "completely-cylinder-periodic": [{"cylinder_periodic_directions": 0, "undetermined_directions": 0, "value": false}]}

        """
        if self._resolved != Goal.COMPLETED:
            await self._report.result(
                self,
                result,
                cylinder_periodic_directions=self._cylinder_periodic_directions,
                undetermined_directions=self._undetermined_directions,
                **kwargs,
            )
