r"""
Determines whether a surface decomposes completely into cylinders in some direction.

Naturally, this can only be decided partially, i.e., we can say, "yes", there
is such a direction but we can never say "no" _all_ directions have a
non-cylinder.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
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

from flatsurvey.pipeline import Goal
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand


class CylinderPeriodicDirection(Goal):
    r"""
    Determines whether there is a direction for which the surface decomposes
    into cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting import Report
        >>> from flatsurvey.cache import Cache, Pickles
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CylinderPeriodicDirection(report=Report([]), flow_decompositions=flow_decompositions, cache=Cache(pickles=Pickles()))
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
            producers=[flow_decompositions], cache=cache, cache_only=cache_only
        )

        self._directions = 0

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Report
            >>> from flatsurvey.cache import Cache, Pickles
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> make_goal = lambda cache: CylinderPeriodicDirection(report=Report([]), flow_decompositions=flow_decompositions, cache=cache)

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = make_goal(Cache(pickles=Pickles()))
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from io import StringIO
            >>> goal = make_goal(Cache(jsons=[StringIO(
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
            ... }]}''')], pickles=Pickles()))
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        """
        results = self._cache.results(
            job=self, predicate=self._flow_decompositions._surface.cache_predicate
        )

        verdict = await results.reduce()

        if verdict is not None or self._cache_only:
            await self._report.result(self, verdict, cached=True)
            self._resolved = Goal.COMPLETED

    @classmethod
    def reduce(cls, results):
        r"""
        Merge results of various runs into a final verdict.

        EXAMPLES::

            >>> CylinderPeriodicDirection.reduce([{"result": None}, {"result": None}])
            >>> CylinderPeriodicDirection.reduce([{"result": True}, {"result": None}])
            True

        """
        results = [result["result"] for result in results]

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

    def command(self):
        command = ["cylinder-periodic-direction"]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        if self._cache_only != self.DEFAULT_CACHE_ONLY:
            command.append("--cache-only")
        return command

    async def _consume(self, decomposition, cost):
        r"""
        Determine wheter ``decomposition`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.cache import Cache, Pickles
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> cpd = CylinderPeriodicDirection(report=Report([log]), flow_decompositions=flow_decompositions, cache=Cache(pickles=Pickles()))

        Investigate in a single direction. We find that this direction is
        cylinder periodic::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            [Ngon([1, 1, 1])] [CylinderPeriodicDirection] True (directions: 1)
            True

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
