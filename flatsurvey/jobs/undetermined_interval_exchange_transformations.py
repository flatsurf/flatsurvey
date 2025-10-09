r"""
Track Interval Exchange Transformations for which it cannot be decided how they
split into cylinders and minimal components.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "undetermined-iets", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker undetermined-iets [OPTIONS]
      Tracks undetermined Interval Exchange Transformations.
      Records Interval Exchange Transformations for which we could not decide how
      they decompose into cylinders and minimal components.
    Options:
      --limit INTEGER  Zorich induction steps to perform before giving up  [default:
                       256]
      --cache-only     Do not perform any computation. Only query the cache.
      --help           Show this message and exit.

Verify that this goal works in a non-survey run::

    >>> invoke(worker, "ngon", "-a", "1", "-a", "1", "-a", "1", "undetermined-iets", "saddle-connections", "--limit", "256")

TESTS:

Verify that this goal works in a tiny survey run (we limit Rauzy induction
steps so that some IETs appear to be undetermined)::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--quiet", "ngons", "--count", "2", "--vertices", "3", "undetermined-iets", "--limit", "1", "saddle-connections", "--limit", "64", "flow-decompositions", "--limit", "1", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir / "ngon-1-2-4.json", tmpdir / "ngon-2-2-3.json"]))

All reported IETs are defined over a number field of degree 6::

    >>> iets = cache.get("undetermined-iets")
    >>> iets
    52 cached results
    >>> iets.degree
    6

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2021-2025 Julian Rüth
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

import time

import click

from flatsurvey.cache import Cache
from flatsurvey.jobs.flow_decompositions import FlowDecompositions
from flatsurvey.jobs.saddle_connection_orientations import SaddleConnectionOrientations
from flatsurvey.pipeline import Bindings, Consumer, Goal
from flatsurvey.reporting import Report
from flatsurvey.surfaces import Surface
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class UndeterminedIntervalExchangeTransformations(Consumer, Command):
    r"""
    Tracks undetermined Interval Exchange Transformations.

    Records Interval Exchange Transformations for which we could not decide how
    they decompose into cylinders and minimal components.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, SaddleConnectionOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> orientations = SaddleConnectionOrientations(connections)
        >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
        >>> UndeterminedIntervalExchangeTransformations(surface=surface, flow_decompositions=flow_decompositions, saddle_connection_orientations=orientations, cache=None)
        undetermined-iets

    """

    DEFAULT_LIMIT = 256

    def __init__(
        self,
        surface: Surface,
        flow_decompositions: FlowDecompositions,
        saddle_connection_orientations: SaddleConnectionOrientations,
        cache: Cache,
        cache_only=Consumer.DEFAULT_CACHE_ONLY,
        limit=DEFAULT_LIMIT,
        report: Report | None = None,
    ):
        self._surface = surface
        self._saddle_connection_orientations = saddle_connection_orientations
        self._limit = limit

        super().__init__(
            producers=[flow_decompositions],
            report=report,
            cache=cache,
            cache_only=cache_only,
        )

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        This can't really "resolve" this goal but it will print some IETs that
        we found in the past if `--cache-only`` has been set.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.reporting.log import Log
            >>> from flatsurvey.reporting import Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> saddle_connection_orientations = SaddleConnectionOrientations(saddle_connections=SaddleConnections(surface=surface))
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=saddle_connection_orientations)
            >>> log = Log({Surface: surface}, output="-")

        We mock some artificial results from previous runs and consume that
        artificial cache. Since we set ``--cache-only``, a result is reported
        immediately::

            >>> import asyncio
            >>> cache = Cache({
            ...     "undetermined-iets": [{
            ...         "surface": {
            ...             "type": "Ngon",
            ...             "angles": [1, 1, 1]
            ...         },
            ...         "value": "some IET",
            ...         "saf": 1337,
            ...     }, {
            ...       "surface": {
            ...           "type": "Ngon",
            ...           "angles": [1, 1, 1]
            ...       },
            ...       "value": "another IETs",
            ...     }]
            ... })
            >>> goal = UndeterminedIntervalExchangeTransformations(report=Report([log]), surface=surface, flow_decompositions=flow_decompositions, saddle_connection_orientations=saddle_connection_orientations, cache=cache, cache_only=True)

            >>> asyncio.run(goal.consume_cache())
            [Ngon([1, 1, 1])] [UndeterminedIntervalExchangeTransformations] some IET (cached) ...
            [Ngon([1, 1, 1])] [UndeterminedIntervalExchangeTransformations] another IETs (cached) ...

        The goal is marked as completed, since we had set ``cache_only`` above::

            >>> goal.resolved
            True

        """
        if not self._cache_only:
            # There's no value in just reproducing existing results.
            return

        results = self._cache.get(UndeterminedIntervalExchangeTransformations).filter(
            self._surface.cache_predicate(True, cache=self._cache)
        )

        for result in results:
            keys = result.keys()
            keys.remove("value")
            await self._report.result(
                self,
                result.value,
                cached=True,
                **{key: getattr(result, key) for key in keys}
            )

        self._resolved = True

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return an ``UndeterminedIntervalExchangeTransformations`` instance from
        the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(UndeterminedIntervalExchangeTransformations.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> UndeterminedIntervalExchangeTransformations.create(bindings)
            undetermined-iets

        """
        with bindings.scope(UndeterminedIntervalExchangeTransformations) as scoped:
            return UndeterminedIntervalExchangeTransformations(
                surface=bindings.get(Surface),
                report=bindings.get(Report),
                flow_decompositions=bindings.get(FlowDecompositions),
                saddle_connection_orientations=bindings.get(
                    SaddleConnectionOrientations
                ),
                cache=bindings.get(Cache),
                cache_only=scoped.get("cache_only", Consumer.DEFAULT_CACHE_ONLY),
                limit=scoped.get(
                    "limit", UndeterminedIntervalExchangeTransformations.DEFAULT_LIMIT
                ),
            )

    @staticmethod
    @click.command(
        name="undetermined-iets",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        show_default=True,
        help="Zorich induction steps to perform before giving up",
    )
    @Consumer._cache_only_option
    @Bindings.click
    def click(bindings: Bindings, limit, cache_only):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(UndeterminedIntervalExchangeTransformations.click)

        """
        bindings.append(list[Goal], UndeterminedIntervalExchangeTransformations)
        with bindings.scope(UndeterminedIntervalExchangeTransformations) as scoped:
            scoped.define(
                limit=limit,
                cache_only=cache_only,
            )

    async def _consume(self, product, cost):
        r"""
        Track any undetermined IETs in the decomposition ``product``.

        EXAMPLES:

        We look at flow decompositions in the (1, 3, 5) surface and limit to a
        single Rauzy induction step so we artificially create some
        "undetermined" IETs here::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Reporter, Log
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections
            >>> surface = Ngon([1, 3, 5])
            >>> bindings = Bindings()
            >>> bindings.define(Surface, surface)
            >>> bindings.append(list[Reporter], Log({Surface: surface}, output="-"))
            >>> with bindings.scope(SaddleConnections) as scoped: scoped.define(limit=73)
            >>> with bindings.scope(FlowDecompositions) as scoped: scoped.define(limit=1)
            >>> with bindings.scope(UndeterminedIntervalExchangeTransformations) as scoped: scoped.define(limit=1)
            >>> uiet = bindings.get(UndeterminedIntervalExchangeTransformations)

            >>> import asyncio
            >>> asyncio.run(uiet.resolve())
            [Ngon([1, 3, 5])] [UndeterminedIntervalExchangeTransformations] ...
            False

        """
        for component in product.components():
            if component.withoutPeriodicTrajectory():
                continue
            if component.cylinder():
                continue

            # Rauzy-inductions are much cheaper when run without the attached
            # surface machinery. So we run some more to verify that we actually
            # fail to certify this IET even when trying much harder.
            iet = component.dynamicalComponent().iet()
            start = time.perf_counter()
            if str(iet.induce(self._limit)) != "LIMIT_REACHED":
                continue
            cost += time.perf_counter() - start

            # Get a fresh copy of the IET (without the coefficient bloat that
            # the previous induce() created)
            iet = component.dynamicalComponent().iet()

            # We cannot fully pickle the C++ IET yet. We try to capture the
            # permutation and the lengths; though this is currently only
            # implemented for e-antic legnths.

            import cppyy
            import pyeantic  # for length pickling

            del pyeantic
            import gmpxxyy  # for SAF pickling

            del gmpxxyy
            cppyy.include("boost/type_erasure/any_cast.hpp")

            to_eantic = cppyy.gbl.boost.type_erasure.any_cast[
                cppyy.gbl.eantic.renf_elem_class
            ]

            lengths = [
                to_eantic(iet.lengths().forget().get(label)) for label in iet.top()
            ]
            degree = max(length.parent().degree() for length in lengths)

            top = [str(label) for label in iet.top()]
            bottom = [str(label) for label in iet.bottom()]

            saf = list(iet.safInvariant())

            await self._report.result(
                self,
                str(iet),
                degree=degree,
                intervals=iet.size(),
                top=top,
                bottom=bottom,
                lengths=lengths,
                saf=saf,
                orientation=self._saddle_connection_orientations._current,
            )

        # We keep collection as many IETs as we can.
        return "NOT_COMPLETED"


__test__ = {
    # doctests of click do not run unless explicitly mentioned here due to the click decorator.
    "UndeterminedIntervalExchangeTransformations.click": UndeterminedIntervalExchangeTransformations.click.__doc__,
}
