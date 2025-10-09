r"""
Determines whether a surface decomposes completely into cylinders in all directions.

Naturally, this can only be decided partially, i.e., we can say, "no",
there is some direction with a minimal component but we can never say "yes",
_all_ directions are cylinder periodic.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
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

Verify that this goal works in a non-survey run::

    >>> invoke(worker, "ngon", "-a", "1", "-a", "3", "-a", "11", "completely-cylinder-periodic")  # doctest: +ELLIPSIS
    [CompletelyCylinderPeriodic] False ...

TESTS:

Verify that this goal works in a tiny survey run::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--quiet", "ngons", "--count", "2", "--vertices", "3", "completely-cylinder-periodic", "--limit", "1", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir / "ngon-1-2-4.json", tmpdir / "ngon-2-2-3.json"]))

Validate the results of the "survey"::

    >>> cached = cache.get("completely-cylinder-periodic")
    >>> len(cached)
    2
    >>> cached.value == None
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
from pyflatsurf import flatsurf  # type: ignore

from flatsurvey.cache import Cache
from flatsurvey.jobs.flow_decompositions import FlowDecompositions
from flatsurvey.pipeline import Bindings, Consumer
from flatsurvey.reporting import Report
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class CompletelyCylinderPeriodic(Consumer, Command):
    r"""
    Determines whether for all directions given by saddle connections, the
    decomposition of the surface is completely cylinder periodic, i.e., the
    decomposition consists only of cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CompletelyCylinderPeriodic(flow_decompositions=flow_decompositions, cache=None)
        completely-cylinder-periodic

    """

    DEFAULT_LIMIT = None

    def __init__(
        self,
        flow_decompositions: FlowDecompositions,
        cache: Cache,
        cache_only: bool = Consumer.DEFAULT_CACHE_ONLY,
        limit: int | None = DEFAULT_LIMIT,
        report: Report | None = None,
    ):
        self._flow_decompositions = flow_decompositions
        self._limit = limit

        self._undetermined_directions = 0
        self._cylinder_periodic_directions = 0

        super().__init__(
            producers=[flow_decompositions],
            report=report,
            cache=cache,
            cache_only=cache_only,
        )

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``CompletelyCylinderPeriodic`` instance from the configuration
        registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(CompletelyCylinderPeriodic.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> CompletelyCylinderPeriodic.create(bindings)
            completely-cylinder-periodic

        """
        with bindings.scope(CompletelyCylinderPeriodic) as scoped:
            return CompletelyCylinderPeriodic(
                report=bindings.get(Report),
                flow_decompositions=bindings.get(FlowDecompositions),
                cache=bindings.get(Cache),
                cache_only=scoped.get("cache_only", Consumer.DEFAULT_CACHE_ONLY),
                limit=scoped.get("limit", CompletelyCylinderPeriodic.DEFAULT_LIMIT),
            )

    @staticmethod
    @click.command(
        name="completely-cylinder-periodic",
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
            >>> invoke_subcommand(CompletelyCylinderPeriodic.click)

        """
        from flatsurvey.pipeline import Goal

        bindings.append(list[Goal], CompletelyCylinderPeriodic)

        with bindings.scope(CompletelyCylinderPeriodic) as scoped:
            scoped.define(limit=limit)
            scoped.define(cache_only=cache_only)

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

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
            >>> log = Report([Json({Surface: surface}, output="-")])

            >>> from io import StringIO
            >>> goal = make_goal(Cache({
            ...     "completely-cylinder-periodic": [{
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
            ...         "value": False,
            ...     }]
            ... }), log)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        The cached verdict can be reported back in JSON format::

            >>> log.flush()  # doctest: +ELLIPSIS
            {"surface": {...}, "completely-cylinder-periodic": [{"timestamp": ..., "cached": true, "value": false}]}

        """
        with self._cache.defaults({"value": None}):
            results = self._cache.get(CompletelyCylinderPeriodic).filter(
                self._flow_decompositions._surface.cache_predicate(
                    True, cache=self._cache
                ),
            )

            verdict = None
            if results.any(lambda result: result.value == False):
                verdict = False

        if verdict is not None or self._cache_only:
            await self._report.result(self, verdict, cached=True)
            self._resolved = True

    async def _consume(self, product: flatsurf.FlowDecomposition, cost):
        r"""
        Determine whether ``product`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=Report([log]), flow_decompositions=flow_decompositions, cache=None)

        Investigate in a single direction::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            'NOT_EXHAUSTED'

        Since we have not found any direction that is not cylinder periodic
        (since there are none), we cannot tell whether the surface is
        completely cylinder periodic::

            >>> report = ccp.report()
            >>> asyncio.run(report)
            [Ngon([1, 1, 1])] [CompletelyCylinderPeriodic] ¯\_(ツ)_/¯ (cylinder_periodic_directions: 1) (undetermined_directions: 0)

        """
        del cost  # unused

        if product.minimalComponents():
            await self.report(False, decomposition=product)
            return "COMPLETED"

        if all([component.cylinder() for component in product.components()]):
            self._cylinder_periodic_directions += 1
            if (
                self._limit is not None
                and self._cylinder_periodic_directions >= self._limit
            ):
                await self.report()
                return "COMPLETED"

        if product.undeterminedComponents():
            self._undetermined_directions += 1

        return "NOT_COMPLETED"

    async def report(self, result=None, **kwargs):
        r"""
        Report whether this surface is completely cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Json, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 11))
            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=report, flow_decompositions=flow_decompositions, cache=None)

        Report that we found a direction that is not a cylinder::

            >>> import asyncio
            >>> asyncio.run(ccp.report(result=False))

            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {...}, "completely-cylinder-periodic": [{"timestamp": ..., "cylinder_periodic_directions": 0, "undetermined_directions": 0, "value": false}]}

        """
        if not self.reported():
            await self._report.result(
                self,
                result,
                cylinder_periodic_directions=self._cylinder_periodic_directions,
                undetermined_directions=self._undetermined_directions,
                **kwargs,
            )


__test__ = {
    # doctests of CompletelyCylinderPeriodic.click do not run unless explicitly mentioned here due to the click decorator.
    "CompletelyCylinderPeriodic.click": CompletelyCylinderPeriodic.click.__doc__,
}
