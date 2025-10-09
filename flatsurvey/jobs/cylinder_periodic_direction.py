r"""
Determines whether a surface decomposes completely into cylinders in some direction.

Naturally, this can only be decided partially, i.e., we can say, "yes", there
is such a direction but we can never say "no" _all_ directions have a
non-cylinder.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "cylinder-periodic-direction", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker cylinder-periodic-direction [OPTIONS]
      Determines whether there is a direction for which the surface decomposes
      into cylinders.
    Options:
      --limit INTEGER  stop search after having looked at that many flow
                       decompositions  [default: no limit]
      --cache-only     Do not perform any computation. Only query the cache.
      --help           Show this message and exit.

Verify that this goal works in a non-survey run::

    >>> invoke(worker, "ngon", "-a", "1", "-a", "3", "-a", "11", "cylinder-periodic-direction")  # doctest: +ELLIPSIS
    [CylinderPeriodicDirection] True ...

TESTS:

Verify that this goal works in a tiny survey run::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--quiet", "ngons", "--count", "2", "--vertices", "3", "cylinder-periodic-direction", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir / "ngon-1-2-4.json", tmpdir / "ngon-2-2-3.json"]))

Validate the results of the "survey"::

    >>> cached = cache.get("cylinder-periodic-direction")
    >>> len(cached)
    2
    >>> cached.value
    True

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

from flatsurvey.cache import Cache
from flatsurvey.jobs.flow_decompositions import FlowDecompositions
from flatsurvey.pipeline import Bindings, Consumer
from flatsurvey.reporting import Report
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class CylinderPeriodicDirection(Consumer, Command):
    r"""
    Determines whether there is a direction for which the surface decomposes
    into cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CylinderPeriodicDirection(flow_decompositions=flow_decompositions, cache=None)
        cylinder-periodic-direction

    """

    DEFAULT_LIMIT = None

    def __init__(
        self,
        flow_decompositions: FlowDecompositions,
        cache: Cache,
        cache_only=Consumer.DEFAULT_CACHE_ONLY,
        limit=DEFAULT_LIMIT,
        report: Report | None = None,
    ):
        super().__init__(
            producers=[flow_decompositions],
            report=report,
            cache=cache,
            cache_only=cache_only,
        )

        self._flow_decompositions = flow_decompositions
        self._limit = limit

        self._directions = 0

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = CylinderPeriodicDirection(flow_decompositions=flow_decompositions, cache=None)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from io import StringIO
            >>> cache = Cache({
            ...     "cylinder-periodic-direction": [{
            ...         "surface": {
            ...             "type": "Ngon",
            ...             "angles": [1, 1, 1],
            ...         },
            ...         "value": None,
            ...     }, {
            ...         "surface": {
            ...             "type": "Ngon",
            ...             "angles": [1, 1, 1],
            ...         },
            ...         "value": True,
            ...     }]
            ... })
            >>> goal = CylinderPeriodicDirection(flow_decompositions=flow_decompositions, cache=cache)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        TESTS:

        Check that the JSON output for this goal works::

            >>> from flatsurvey.reporting import Json, Report

            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> goal = CylinderPeriodicDirection(report=report, flow_decompositions=flow_decompositions, cache=cache)

            >>> import asyncio
            >>> asyncio.run(goal.consume_cache())
            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "cylinder-periodic-direction": [{"timestamp": "...", "cached": true, "value": true}]}

        """
        with self._cache.defaults({"value": None}):
            results = self._cache.get(CylinderPeriodicDirection).filter(
                self._flow_decompositions._surface.cache_predicate(
                    True, cache=self._cache
                ),
            )

            verdict = None
            if results.any(lambda result: result.value == True):
                verdict = True

        if verdict is not None or self._cache_only:
            await self._report.result(self, verdict, cached=True)
            self._resolved = True

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``CylinderPeriodicDirection`` instance from the configuration
        registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(CylinderPeriodicDirection.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> CylinderPeriodicDirection.create(bindings)
            cylinder-periodic-direction

        """
        with bindings.scope(CylinderPeriodicDirection) as scoped:
            return CylinderPeriodicDirection(
                report=bindings.get(Report),
                flow_decompositions=bindings.get(FlowDecompositions),
                cache=bindings.get(Cache),
                cache_only=scoped.get(
                    "cache_only", lambda: Consumer.DEFAULT_CACHE_ONLY
                ),
                limit=scoped.get(
                    "limit", lambda: CylinderPeriodicDirection.DEFAULT_LIMIT
                ),
            )

    @staticmethod
    @click.command(
        name="cylinder-periodic-direction",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="stop search after having looked at that many flow decompositions  [default: no limit]",
    )
    @Consumer._cache_only_option
    @Bindings.click
    def click(bindings: Bindings, limit, cache_only):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(CylinderPeriodicDirection.click)

        """
        from flatsurvey.pipeline import Goal

        bindings.append(list[Goal], CylinderPeriodicDirection)

        with bindings.scope(CylinderPeriodicDirection) as scoped:
            scoped.define(limit=limit)
            scoped.define(cache_only=cache_only)

    async def _consume(self, product, cost):
        r"""
        Determine whether ``decomposition`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> cpd = CylinderPeriodicDirection(report=Report([log]), flow_decompositions=flow_decompositions, cache=None)

        Investigate in a single direction. We find that this direction is
        cylinder periodic::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            [Ngon([1, 1, 1])] [CylinderPeriodicDirection] True (directions: 1) (decomposition: FlowDecomposition with 1 cylinders, 0 minimal components and 0 undetermined components)
            'NOT_EXHAUSTED'

        TESTS:

        Verify that the JSON output works::

            >>> from flatsurvey.reporting import Json, Report

            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> cpd = CylinderPeriodicDirection(report=report, flow_decompositions=flow_decompositions, cache=None)

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            'NOT_EXHAUSTED'

            >>> asyncio.run(cpd.report())
            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {...}, "cylinder-periodic-direction": [{"timestamp": "...", "directions": 1, "decomposition": {...}, "value": true}]}

            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "cylinder-periodic-direction": [{"timestamp": ..., "directions": 1, "value": true, "decomposition": {...}}]}

        """
        del cost

        self._directions += 1

        if all([component.cylinder() for component in product.components()]):
            await self.report(True, decomposition=product)
            return "COMPLETED"

        if self._limit is not None and self._directions >= self._limit:
            await self.report()
            return "COMPLETED"

        return "NOT_COMPLETED"

    async def report(self, result=None, **kwargs):
        r"""
        Report whether this surface has a cylinder periodic direction.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Json, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 11))
            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> cpd = CylinderPeriodicDirection(report=report, flow_decompositions=flow_decompositions, cache=None)

        Report that we found a direction that is cylinder periodic::

            >>> import asyncio
            >>> asyncio.run(cpd.report(result=True))

            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {...}, "cylinder-periodic-direction": [{"timestamp": "...", "directions": 0, "value": true}]}

        """
        if not self.reported():
            await self._report.result(
                self, result, directions=self._directions, **kwargs
            )


__test__ = {
    # doctests of CompletelyCylinderPeriodic.click do not run unless explicitly mentioned here due to the click decorator.
    "CylinderPeriodicDirection.click": CylinderPeriodicDirection.click.__doc__,
}
