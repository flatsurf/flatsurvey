r"""
Computes the GL₂(R) orbit closure of a surface.

Naturally, this will only find a lower bound for the orbit closure, i.e., the
space it finds might be too small because not enough directions have been
investigated that would lead us to the full space.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "orbit-closure", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker orbit-closure [OPTIONS]
      Determines the GL₂(R) orbit closure of ``surface``.
    Options:
      --limit INTEGER             stop after having looked at that many flow
                                  decompositions  [default: no limit]
      --stale-limit TEXT          expand the search radius after processing that
                                  many flow decompositions with cylinders without an
                                  increase in dimension; if not an integer, then
                                  this is parsed as a pandas timedelta and the
                                  expansion happens after that time has passed
                                  without an improvement  [default: 128]
      --expansions-limit INTEGER  when the --stale-limit has been reached, continue
                                  the search with random saddle connections that are
                                  twice as long as the ones used previously; repeat
                                  this doubling process that many times; once the
                                  limit has been reached, the search continues
                                  indefinitely  [default: <class 'int'>]
      --deform-limit TEXT         if set, deform the input surface after finding
                                  that many flow decompositions with cylinders
                                  without an increase in dimension; if not an
                                  integer, then this is parsed as a pandas timedelta
                                  and we deform after that time has passed without
                                  an improvement
      --no-symmetries             disable preferred exploration of identical
                                  directions modulo symmetries of the surface for
                                  directions that lead to an increase in orbit
                                  closure dimension
      --cache-only                Do not perform any computation. Only query the
                                  cache.
      --help                      Show this message and exit.

Verify that this goal works in a non-survey run::

    >>> invoke(worker, "ngon", "-a", "1", "-a", "2", "-a", "4", "orbit-closure")  # doctest: +ELLIPSIS
    [OrbitClosure] ...
    [OrbitClosure] GL(2,R)-orbit closure of dimension at least 7 in H_3(3, 1) (ambient dimension 7) (dimension: 7) (dimension_upper_bound: 7) (directions: 6) (directions_with_cylinders: 6) (dense: True) (stratum: H_3(3, 1))

TESTS:

Verify that we can determine that some small surfaces have dense orbit closure::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--quiet", "ngons", "--count=4", "--vertices=3", "orbit-closure", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir]))

    >>> cached = cache.get("orbit-closure")
    >>> len(cached)
    4
    >>> cached.dense
    True

Verify that some small surfaces from the literature do not have dense orbit
closure::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--quiet", "ngons", "--literature=only", "--count=4", "--vertices=3", "orbit-closure", "--limit=128", "--deform-limit=20", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir]))

    >>> cached = cache.get("orbit-closure")
    >>> cached = cached.filter(lambda row: row.dimension_upper_bound != 2)
    >>> len(cached)
    2
    >>> cached.dense is None
    True

Verify that this also works if we set a runtime limit instead of an explicit
limit::

    >>> from pathlib import Path
    >>> from flatsurvey.survey import survey
    >>> from flatsurvey.reporting import Json
    >>> from tempfile import TemporaryDirectory

    >>> with TemporaryDirectory() as tmpdir:
    ...     tmpdir = Path(tmpdir)
    ...     invoke(survey, "--debug", "--time-limit=00:00:10", "--quiet", "ngons", "--literature=only", "--count=4", "--vertices=3", "orbit-closure", "--deform-limit=20", "json", "--prefix", tmpdir)
    ...     cache = Cache(Cache.load([tmpdir]))

    >>> cached = cache.get("orbit-closure")
    >>> cached = cached.filter(lambda row: row.dimension_upper_bound != 2)
    >>> cached.dense is None
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

import datetime
from dataclasses import dataclass, field

import click
from sage.misc.cachefunc import cached_method

from flatsurvey.cache import Cache
from flatsurvey.jobs.flow_decompositions import FlowDecompositions
from flatsurvey.jobs.saddle_connection_orientations import SaddleConnectionOrientations
from flatsurvey.jobs.saddle_connections import SaddleConnections
from flatsurvey.pipeline import Bindings, Consumer, Goal
from flatsurvey.reporting import Report
from flatsurvey.surfaces import Deformation, Surface
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


@dataclass
class Statistics:
    start: datetime.datetime = field(default_factory=lambda: datetime.datetime.now())
    # The number of saddle connection directions that we have investigated
    directions: int = 0
    # The number of flow decompositions we have processed that contained at
    # least one cylinder
    directions_with_cylinders: int = 0
    # The shortest saddle connection we have seen.
    shortest_saddle_connection_holonomy = None
    # The longest saddle connection we have seen.
    longest_saddle_connection_holonomy = None

    @property
    def timedelta(self) -> datetime.timedelta:
        return datetime.datetime.now() - self.start


class OrbitClosure(Consumer, Command):
    r"""
    Determines the GL₂(R) orbit closure of ``surface``.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> orientations = SaddleConnectionOrientations(connections)
        >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
        >>> OrbitClosure(surface=surface, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)
        orbit-closure

    """

    DEFAULT_LIMIT = None
    DEFAULT_STALE_LIMIT = 128
    DEFAULT_DEFORM_LIMIT = None
    DEFAULT_SYMMETRIES = True

    def __init__(
        self,
        surface: Surface,
        flow_decompositions: FlowDecompositions,
        saddle_connection_orientations: SaddleConnectionOrientations,
        saddle_connections: SaddleConnections,
        cache: Cache,
        limit: int | None = DEFAULT_LIMIT,
        stale_limit: int | datetime.timedelta = DEFAULT_STALE_LIMIT,
        deform_limit=DEFAULT_DEFORM_LIMIT,
        symmetries=DEFAULT_SYMMETRIES,
        cache_only=Consumer.DEFAULT_CACHE_ONLY,
        report: Report | None = None,
    ):
        super().__init__(
            producers=[flow_decompositions],
            report=report,
            cache=cache,
            cache_only=cache_only,
        )

        self._surface = surface
        self._flow_decompositions = flow_decompositions
        self._saddle_connection_orientations = saddle_connection_orientations
        self._saddle_connections = saddle_connections
        self._limit = limit
        self._stale_limit = stale_limit
        self._deform_limit = deform_limit
        self._symmetries = symmetries
        self._cache_only = cache_only

        self._statistics = Statistics()
        self._statistics_since_expansion = Statistics()
        self._statistics_since_augmentation = Statistics()
        self._statistics_since_augmentation_in_expansion = Statistics()

    async def consume_cache(self):
        r"""
        Try to resolve this goal from cached previous runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> from flatsurvey.cache import Cache
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = OrbitClosure(surface=surface, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from io import StringIO
            >>> cache = Cache({
            ...     "orbit-closure": [{
            ...         "surface": {
            ...             "type": "Ngon",
            ...             "angles": [1, 1, 1],
            ...         },
            ...         "dense": None,
            ...     }, {
            ...         "surface": {
            ...             "type": "Ngon",
            ...             "angles": [1, 1, 1],
            ...         },
            ...         "dense": True,
            ... }]})

            >>> goal = OrbitClosure(surface=surface, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=cache)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        TESTS:

        Check that JSON output for this goal works::

            >>> from flatsurvey.reporting import Json, Report

            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> goal = OrbitClosure(surface=surface, report=report, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=cache)

            >>> import asyncio
            >>> asyncio.run(goal.consume_cache())
            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "orbit-closure": [{"timestamp": "...", "dense": true, "cached": true, "value": null}]}


        """
        with self._cache.defaults({"dense": None}):
            results = self._cache.get(OrbitClosure).filter(
                self._surface.cache_predicate(False, cache=self._cache)
            )

            verdict = None
            if results.any(lambda result: result.dense == True):
                verdict = True

        if verdict is not None or self._cache_only:
            await self._report.result(self, result=None, dense=verdict, cached=True)
            self._resolved = True

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return an ``OrbitClosure`` instance from the configuration
        registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> OrbitClosure.create(bindings)
            orbit-closure

        """
        with bindings.scope(OrbitClosure) as scoped:
            return OrbitClosure(
                surface=bindings.get(Surface),
                report=bindings.get(Report),
                flow_decompositions=bindings.get(FlowDecompositions),
                saddle_connection_orientations=bindings.get(
                    SaddleConnectionOrientations
                ),
                saddle_connections=bindings.get(SaddleConnections),
                cache=bindings.get(Cache),
                limit=scoped.get("limit", lambda: OrbitClosure.DEFAULT_LIMIT),
                stale_limit=scoped.get("stale_limit", OrbitClosure.DEFAULT_STALE_LIMIT),
                deform_limit=scoped.get(
                    "deform_limit", lambda: OrbitClosure.DEFAULT_DEFORM_LIMIT
                ),
                symmetries=scoped.get("symmetries", OrbitClosure.DEFAULT_SYMMETRIES),
                cache_only=scoped.get("cache_only", Consumer.DEFAULT_CACHE_ONLY),
            )

    @staticmethod
    @click.command(
        name="orbit-closure",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--limit",
        type=int,
        default=None,
        help="stop after having looked at that many flow decompositions  [default: no limit]",
    )
    @click.option(
        "--stale-limit",
        type=str,
        default=DEFAULT_STALE_LIMIT,
        show_default=True,
        help="expand the search radius after processing that many flow decompositions with cylinders without an increase in dimension; if not an integer, then this is parsed as a pandas timedelta and the expansion happens after that time has passed without an improvement",
    )
    @click.option(
        "--expansions-limit",
        type=int,
        default=int,
        show_default=2,
        help="when the --stale-limit has been reached, continue the search with random saddle connections that are twice as long as the ones used previously; repeat this doubling process that many times; once the limit has been reached, the search continues indefinitely",
    )
    @click.option(
        "--deform-limit",
        type=str,
        default=DEFAULT_DEFORM_LIMIT,
        help="if set, deform the input surface after finding that many flow decompositions with cylinders without an increase in dimension; if not an integer, then this is parsed as a pandas timedelta and we deform after that time has passed without an improvement",
    )
    @click.option(
        "--no-symmetries",
        is_flag=True,
        help="disable preferred exploration of identical directions modulo symmetries of the surface for directions that lead to an increase in orbit closure dimension",
    )
    @Consumer._cache_only_option
    @Bindings.click
    def click(
        bindings: Bindings,
        limit,
        stale_limit,
        expansions_limit,
        deform_limit,
        no_symmetries,
        cache_only,
    ):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(OrbitClosure.click)

        """
        try:
            stale_limit = int(stale_limit)
        except ValueError:
            import pandas

            stale_limit = pandas.Timedelta(stale_limit).to_pytimedelta()  # type: ignore

        assert isinstance(stale_limit, (int, datetime.timedelta))

        if deform_limit is not None:
            try:
                deform_limit = int(deform_limit)
            except ValueError:
                import pandas

                deform_limit = pandas.Timedelta(deform_limit).to_pytimedelta()  # type: ignore

            assert isinstance(deform_limit, (int, datetime.timedelta))

        bindings.append(list[Goal], OrbitClosure)
        with bindings.scope(OrbitClosure) as scoped:
            scoped.define(
                limit=limit,
                stale_limit=stale_limit,
                expansions_limit=expansions_limit,
                deform_limit=deform_limit,
                symmetries=not no_symmetries,
                cache_only=cache_only,
            )

    @property
    def dimension(self):
        r"""
        Return the currently determined lower bound for the dimension of the orbit closure.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> oc.dimension
            2

        """
        return self._orbit_closure().dimension()

    @cached_method
    def _orbit_closure(self):
        r"""
        Return the orbit closure of the surface (as has been determined so far.)

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> oc._orbit_closure()
            GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2)

        """
        from flatsurf import GL2ROrbitClosure

        return GL2ROrbitClosure(self._surface.surface())

    @property
    def dense(self):
        r"""
        Return whether the orbit closure has already been determined to be dense.

        Returns ``None`` when there is no verdict yet.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> oc.dense
            True

        """
        if self.dimension == self._surface.orbit_closure_dimension_upper_bound:
            return True

        return None

    def _consume_augment_orbit_closure(self, flow_decomposition) -> int:
        r"""
        Attempt to augment the orbit closure with the cylinders in ``flow_decomposition``.

        Return by how much the dimension increased.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> decomposition = oc._orbit_closure().decomposition((1, 0))
            >>> decomposition
            FlowDecomposition with 5 cylinders, 0 minimal components and 0 undetermined components
            >>> oc._consume_augment_orbit_closure(decomposition)
            3

            >>> decomposition = oc._orbit_closure().decomposition((1, 1))
            >>> decomposition
            FlowDecomposition with 0 cylinders, 1 minimal components and 0 undetermined components
            >>> oc._consume_augment_orbit_closure(decomposition)
            0

        """
        orbit_closure = self._orbit_closure()

        dimension = orbit_closure.dimension()

        orbit_closure.update_tangent_space_from_flow_decomposition(flow_decomposition)

        self._report.progress(
            source=self,
            what="dimension",
            count=self.dimension,
            total=self._surface.orbit_closure_dimension_upper_bound,
        )

        assert self.dimension <= self._surface.orbit_closure_dimension_upper_bound

        return orbit_closure.dimension() - dimension

    def _consume_update_statistics(
        self, saddle_connection, flow_decomposition, dimension_increase: int
    ) -> None:
        r"""
        Update the internal statistics we collect on the orbit closure search.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, "--stale-limit=2", bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

        We generate somewhat artificially a saddle connection and a flow
        decomposition for demo purposes::

            >>> decomposition = oc._orbit_closure().decomposition((1, 0))

            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current

        ::

            >>> oc._consume_update_statistics(saddle_connection, decomposition, dimension_increase=0)

            >>> oc._statistics.directions_with_cylinders
            1
            >>> oc._statistics_since_augmentation.directions_with_cylinders
            1

        ::

            >>> oc._consume_update_statistics(saddle_connection, decomposition, dimension_increase=3)
            >>> oc._statistics.directions_with_cylinders
            2
            >>> oc._statistics_since_augmentation.directions_with_cylinders
            0

        """
        for statistics in [
            self._statistics,
            self._statistics_since_augmentation,
            self._statistics_since_augmentation_in_expansion,
        ]:
            statistics.directions += 1

            if flow_decomposition.cylinders():
                statistics.directions_with_cylinders += 1

            from flatsurf.geometry.pyflatsurf.conversion import VectorSpaceConversion

            holonomy = saddle_connection.vector()
            conversion = VectorSpaceConversion.from_pyflatsurf_from_elements([holonomy])
            holonomy = conversion.section(holonomy)

            def length2(v):
                return v.dot_product(v)

            statistics.shortest_saddle_connection_holonomy = (
                statistics.shortest_saddle_connection_holonomy or holonomy
            )
            if length2(holonomy) < length2(
                statistics.shortest_saddle_connection_holonomy
            ):
                statistics.shortest_saddle_connection_holonomy = holonomy

            statistics.longest_saddle_connection_holonomy = (
                statistics.longest_saddle_connection_holonomy or holonomy
            )
            if length2(holonomy) > length2(
                statistics.shortest_saddle_connection_holonomy
            ):
                statistics.longest_saddle_connection_holonomy = holonomy

        if dimension_increase:
            self._statistics_since_augmentation = Statistics()
            self._statistics_since_augmentation_in_expansion = Statistics()

    def _consume_should_expand(self) -> bool:
        r"""
        Return whether we should use saddle connections that are substantially
        larger than the ones we have been trying so far.

        .. NOTE::

            Heuristically, it's sometimes helpful to skip over a range of saddle
            connections and continue with saddle connections that are much larger
            to find cylinders that can contribute again to the orbit closure
            computation.

            Also, we initially iterate over saddle connections by length,, i.e.,
            deterministically. Once we expand, we switch to a random search which
            makes it meaningful to repeat an orbit closure search on deterministic
            surfaces (such as triangles.)

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, "--stale-limit=2", bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> oc._consume_should_expand()
            False

        We generate somewhat artificially a saddle connection and some flow
        decompositions for demo purposes::

            >>> cylinders = oc._orbit_closure().decomposition((1, 0))
            >>> minimal = oc._orbit_closure().decomposition((1, 1))

            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current

        After ``stale_limit`` many directions with cylinders but without
        improvement, we try to expand::

            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)
            >>> oc._consume_should_expand()
            False

            >>> oc._consume_update_statistics(saddle_connection, minimal, dimension_increase=0)
            >>> oc._consume_should_expand()
            False

            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)
            >>> oc._consume_should_expand()
            True

        Actually expanding resets this logic::

            >>> oc._consume_expand()
            >>> oc._consume_should_expand()
            False

            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)
            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)

            >>> oc._consume_should_expand()
            True

        Note that on a surface without dense orbit closure, this will never
        actually stop. You need to set a time limit on the worker to cancel
        eventually or set the ``--limit`` option.

        """
        if self.dense:
            return False

        if isinstance(self._stale_limit, int):
            # We do not take directions without cylinders into account here. If
            # there are a lot of directions without cylinders, then this
            # usually doesn't get better by going further out in the surface;
            # rather, heuristically at least, short directions have more
            # cylinders than long ones.
            if (
                self._statistics_since_augmentation_in_expansion.directions_with_cylinders
                >= self._stale_limit
            ):
                self._report.log(
                    self,
                    f"Found {self._statistics_since_augmentation_in_expansion.directions_with_cylinders} directions with cylinders without a dimension increase since the last expansion. Will expand the search radius again.",
                )
                return True
        elif isinstance(self._stale_limit, datetime.timedelta):
            if (
                self._statistics_since_augmentation_in_expansion.timedelta
                >= self._stale_limit
            ):
                self._report.log(
                    self,
                    f"Found {self._statistics_since_augmentation_in_expansion.directions_with_cylinders} directions with cylinders without a dimension increase in the past {self._statistics_since_augmentation_in_expansion.timedelta} since the last expansion. Will expand the search radius again.",
                )
                return True
        else:
            raise NotImplementedError

        return False

    def _consume_expand(self) -> None:
        r"""
        Randomize the saddle connections that we are considering and only
        consider saddle connections that are at least twice as large as what we
        have seen so far.

        See :meth:`_consume_should_expand` for examples.
        """
        longest = self._statistics.longest_saddle_connection_holonomy

        assert (
            longest is not None
        ), "must not call _consume_expand() before _consume_update_statistics()"

        from flatsurf.geometry.pyflatsurf.conversion import VectorSpaceConversion

        longest = VectorSpaceConversion.to_pyflatsurf(longest.parent())(longest)

        import pyflatsurf

        lower_bound = pyflatsurf.flatsurf.Bound.upper(longest)
        lower_bound *= 2

        self._saddle_connections.randomize(lower_bound)

        self._statistics_since_augmentation_in_expansion = Statistics()

    def _consume_should_deform(self) -> bool:
        r"""
        Return whether we should slightly deform this surface and restart the
        orbit closure search on the deformed surface.

        .. NOTE::

            On a SAF=0 surface, it can happen that we cannot determine the full
            orbit closure no matter how many flow decompositions we feed into
            the system; there are lots of cylinders but the dimension doesn't
            increase anymore.

            On such surfaces, but heuristically also in some other cases, it
            can be beneficial to deform away from the problematic surface a
            little bit and restart the orbit closure search there.

            The downside of such a deformation is that it tends to lead to
            substantial coefficient bloat and therefore slows down all the
            arithmetic.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, "--deform-limit=2", bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> oc._consume_should_deform()
            False

        We generate somewhat artificially a saddle connection and some flow
        decompositions for demo purposes::

            >>> cylinders = oc._orbit_closure().decomposition((1, 0))
            >>> minimal = oc._orbit_closure().decomposition((1, 1))

            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current

        After ``deform`` many directions with cylinders but without
        improvement, we try to deform::

            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)
            >>> oc._consume_should_deform()
            False

            >>> oc._consume_update_statistics(saddle_connection, minimal, dimension_increase=0)
            >>> oc._consume_should_deform()
            False

            >>> oc._consume_update_statistics(saddle_connection, cylinders, dimension_increase=0)
            >>> oc._consume_should_deform()
            False

        However, we have no directions in which to deform yet in a
        2-dimensional orbit closure, so we need to increase the dimension first::

            >>> oc._consume_augment_orbit_closure(cylinders)
            3

            >>> oc._consume_should_deform()
            True

        Expanding does not reset this logic::

            >>> oc._consume_expand()
            >>> oc._consume_should_deform()
            True

        """
        if self.dense:
            return False

        if self._deform_limit is None:
            return False

        from flatsurvey.surfaces.deformation import Deformation

        if isinstance(self._surface, Deformation):
            # We don't re-deform a surface. This just leads to coefficient
            # bloat and is not beneficial in our experiments.
            return False

        if self.dimension == 2:
            # We cannot deform away from SAF=0 if we do not have any
            # non-trivial directions in the tangent space.
            return False

        if isinstance(self._deform_limit, int):
            if (
                self._statistics_since_augmentation.directions_with_cylinders
                >= self._deform_limit
            ):
                self._report.log(
                    self,
                    f"Found {self._statistics_since_augmentation.directions_with_cylinders} directions with cylinders without a dimension increase. Will attempt to deform the surface to improve the situation.",
                )
                return True
        elif isinstance(self._deform_limit, datetime.timedelta):
            if self._statistics_since_augmentation.timedelta >= self._deform_limit:
                self._report.log(
                    self,
                    f"Found {self._statistics_since_augmentation.directions_with_cylinders} directions with cylinders without a dimension increase in the past {self._statistics_since_augmentation.timedelta}. Will attempt to deform the surface to improve the situation.",
                )
                return True
        else:
            raise NotImplementedError

        return False

    def _deformation_tangent_space(self) -> tuple[list, list]:
        r"""
        Return a basis of the tangent space that is suitable for deformation of
        this surface.

        The basis is returned as a pair of lists. Merging both lists produces a
        basis of the tangent space.

        The first list spans the subspace of the tangent space that will lead to
        surfaces that remain in the SAF=0 subspace.

        The second list spans a subspace does not contain any such vectors.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> cylinders = oc._orbit_closure().decomposition((1, 0))
            >>> oc._consume_augment_orbit_closure(cylinders)
            3

            >>> saf0, tangents = oc._deformation_tangent_space()
            >>> len(saf0)
            2
            >>> len(tangents)
            3

        """
        orbit_closure = self._orbit_closure()

        tangents = [orbit_closure.lift(v) for v in orbit_closure.tangent_space_basis()]

        return tangents[:2], tangents[2:]

    def _deformation_small_tangent(self, tangents: list, saf0: list):
        r"""
        Return a vector of small height in the rational vector space with basis
        ``tangents``.

        ALGORITHM:

        We rewrite the basis ``tangents`` as a integral basis of
        lattice, apply the LLL algorithm to determine a short vector.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> cylinders = oc._orbit_closure().decomposition((1, 0))
            >>> oc._consume_augment_orbit_closure(cylinders)
            3

        In this example, we do not find any shorter vectors. It seems that
        basis matrix that sage-flatsurf uses is already LLL reduced::

            >>> saf0, tangents = oc._deformation_tangent_space()
            >>> tangent = oc._deformation_small_tangent(tangents, saf0)
            >>> tangent == tangents[0]
            True

        """
        parent = set(c.parent() for tangent in tangents + saf0 for c in tangent)

        if len(parent) != 1:
            raise NotImplementedError(
                "all coefficients must live in the same number field"
            )

        # A common e-antic and SageMath parent for all vector coefficients
        renf = next(iter(parent))
        parent = renf.number_field

        # Rewrite a basis of a subspace of the tangent space as a matrix describing an integer lattice
        def to_integer_matrix(tangents):
            # Expand each number field element to degree many rational numbers
            from sage.all import QQ, ZZ, Matrix

            degree = parent.degree()
            basis = Matrix(
                QQ,
                len(tangents),
                len(tangents[0]) * degree,
                sum((parent(c).list() for tangent in tangents for c in tangent), []),
            )

            # Rescale to integer coefficients
            basis *= basis.denominator()
            basis = basis.change_ring(ZZ)

            assert basis.rank() == len(tangents)

            return basis

        # Find a short vector
        lll = to_integer_matrix(tangents).LLL()
        tangent = lll[0]

        # Rewrite tangent vector as an actual vector
        from itertools import batched

        from sage.all import vector

        tangent = vector(
            parent(coefficients) for coefficients in batched(tangent, parent.degree())
        )

        # Validate result
        from sage.all import span

        assert tangent in span(tangents)
        assert tangent not in span(saf0)

        self._report.log(
            self,
            f"Chosen short tangent vector has roughly {len(str(tangent))/len(str(saf0[0].change_ring(parent))):.3} the height of a shortest (but ineligible) tangent vector.",
        )

        tangent = tangent.change_ring(renf)

        return tangent

    def _deformation_scale_for_surface(self, tangent) -> list:
        r"""
        Return a list of vectors ``(x, y)`` for a deformation expanding the
        ``i``-th edge by ``x[i], y[i]``. Both the vector of ``x`` components
        and the vector of ``y`` components is a scalar multiple of
        ``tangents``. The returned vector should satisfy:

        * the deformation should be so small that not many flips on the surface
        are needed to move around the vertices

        * the deformation is big enough so that it does actually obviously
        change the geometry of the surface

        * the deformation is such that applying it does not lead to vertices
        colliding

        ALGORITHM:

        We start with ``(prime * tangent, prime' * tangent)`` with random small
        primes so that their direction hopefully does not show up in the
        surface (this takes care of the last requirement above.)

        Then we scale the vector so that its biggest shift on a vertex is in
        (1/6, 1/3] of the length of the shortest saddle connection (this should
        take care of all the requirements above.)

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

        We generate somewhat artificially a saddle connection and a flow
        decompositions for demo purposes::

            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current
            >>> cylinders = oc._orbit_closure().decomposition((1, 0))

        ::

            >>> oc._consume_update_statistics(saddle_connection, cylinders, 0)

            >>> saf0, tangents = oc._deformation_tangent_space()

            >>> xy = oc._deformation_scale_for_surface(saf0[0])

        Verify that the scaled vector is short but not too short in comparison
        to the shortest saddle connection on the surface::

            >>> from sage.all import RR
            >>> shortest = oc._statistics.shortest_saddle_connection_holonomy.change_ring(RR).norm()

            >>> from flatsurf.geometry.pyflatsurf.conversion import VectorSpaceConversion
            >>> conversion = VectorSpaceConversion.from_pyflatsurf_from_elements(xy)

            >>> max_shift = max(conversion.section(v).change_ring(RR).norm() for v in xy)

            >>> shortest / 6 < max_shift <= shortest / 3
            True

        """
        from sage.all import RR, ZZ, random_prime, vector

        renf = tangent.base_ring()
        number_field = renf.number_field

        tangent = tangent.change_ring(number_field)

        p = random_prime(256, lbound=32)
        q = random_prime(512, lbound=p)

        x = p * tangent
        y = q * tangent

        def length2(v):
            return v.dot_product(v)

        # Determine the maximum shift of a vertex that would happen. (As its length squared.)
        shifts = [vector(xy) for xy in zip(x, y)]
        max2 = max(length2(v) for v in shifts)

        # Determine the length squared of the shortest saddle connection.
        shortest = self._statistics.shortest_saddle_connection_holonomy
        shortest2 = length2(shortest)

        # We find a scaling factor 2^n such that the shift is within (1/6,1/3]
        # of the length of the saddle connection.
        n = ZZ(RR(shortest2 / max2 / 36).sqrt().log(2).ceil())

        self._report.log(
            self,
            f"Scaling short tangent vectors for deformation by {p}, {q}, and 2^{n} to scale it to the size of the surface.",
        )

        # Verify that we are roughly in (1/6,1/3]
        assert (
            shortest2 / 37 < (RR(2) ** n) ** 2 * max2 < shortest2 / 8
        ), f"{float(shortest2 / 37)} < {(2**n)**2 * max2} < {float(shortest2)}"

        # Apply the scaling to our vectors.
        x *= ZZ(2) ** n
        y *= ZZ(2) ** n

        self._report.log(
            self,
            f"Tangent vectors for deformation have roughly {len(str(x) + str(y)) / len(str(tangent)):.3} the height of the short tangent vector.",
        )

        x = x.change_ring(renf)
        y = y.change_ring(renf)

        return [self._orbit_closure().V2(*xy).vector for xy in zip(x, y)]

    def _deformation_apply_to_surface(self, deformation_vector) -> Deformation:
        r"""
        Return the surface obtained by applying ``deformation_vector`` to the
        current surface.

        INPUT:

        - ``deformation_vector`` -- a libflatsurf vector with one entry per
          positive edge in the underlying libflatsurf surface

        """
        deformed = self._orbit_closure()._surface + deformation_vector

        surface = deformed.surface()

        surface.delaunay()

        from flatsurf.geometry.pyflatsurf.conversion import (
            FlatTriangulationConversion,
        )

        conversion = FlatTriangulationConversion.from_pyflatsurf(surface)

        return conversion.domain()

    def _deformation_is_saf0(self, surface) -> bool:
        r"""
        Return whether the first IET that we see has SAF=0.

        In the deformation process we try to move away from surfaces with that
        property.

        EXAMPLES:

        We generate two deformed surfaces, one with a deformation that produces
        SAF=0 and one that produces SAF!=0::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)
            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current
            >>> cylinders = oc._orbit_closure().decomposition((1, 0))
            >>> oc._consume_augment_orbit_closure(cylinders)
            3
            >>> oc._consume_update_statistics(saddle_connection, cylinders, 3)

        ::

            >>> saf0, tangents = oc._deformation_tangent_space()

            >>> deformation = oc._deformation_scale_for_surface(saf0[0])
            >>> saf0_surface = oc._deformation_apply_to_surface(deformation)

            >>> deformation = oc._deformation_scale_for_surface(tangents[0])
            >>> surface = oc._deformation_apply_to_surface(deformation)

        ::

            >>> oc._deformation_is_saf0(bindings.get(Surface).surface())
            True

            >>> oc._deformation_is_saf0(saf0_surface)
            True

            >>> oc._deformation_is_saf0(surface)
            False

        """
        from flatsurf import GL2ROrbitClosure

        O = GL2ROrbitClosure(surface)

        label = surface.labels()[0]
        decomposition = O.decomposition(surface.polygon(label).edge(0))
        component = decomposition.components()[0]

        return not any(component.safInvariant())

    def _deformation(self, bindings: Bindings) -> Bindings:
        r"""
        Return a new worker configuration to run this survey on a slightly
        deformed surface.

        See :meth:`_consume_should_deform` for why we pass to a deformation.

        INPUT:

        - ``bindings`` -- the bindings that govern the currently active worker

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon, Surface
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "4", "-a", "6", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

        We generate somewhat artificially a saddle connection and a flow
        and pretend that we had seen this one already. The internals here
        require this to have happened at some point before this function is
        called::

            >>> oc._saddle_connections._produce()
            'NOT_EXHAUSTED'
            >>> saddle_connection = oc._saddle_connections._current
            >>> cylinders = oc._orbit_closure().decomposition((1, 0))

            >>> oc._consume_augment_orbit_closure(cylinders)
            3
            >>> oc._consume_update_statistics(saddle_connection, cylinders, 3)

        Now we produce the bindings to restart with a deformed surface::

            >>> deformed = oc._deformation(bindings)

            >>> deformed.get(Surface)
            Deformation of Ngon([1, 4, 6])

        """
        # We can deform with any linear combination of the tangent vectors in
        # the x and y component. We could just deform with x=tangents[0], y=0
        # essentially. However, there's problems with this:
        # * The first two tangent vectors cannot be used because they do not
        #   move us away from SAF=0.
        # * The tangent vectors often have coefficients with very large height.
        #   We therefore use an LLL approach to find a vector of small height
        #   in their span.
        # * The actual vector could be very long, so there would be lots of
        #   flips necessary on the underlying surface to perform that
        #   deformation. We therefore rescale the vector to be small but not
        #   too small in the surface.
        # * Due to the non-random structure of the surface, deforming only in x
        #   direction can lead to collision of vertices (we detect those but it
        #   means that we'd have to retry many times.)
        saf0, tangents = self._deformation_tangent_space()

        tangent = self._deformation_small_tangent(tangents, saf0)

        deformation_vector = self._deformation_scale_for_surface(tangent)

        surface = self._deformation_apply_to_surface(deformation_vector)

        assert not self._deformation_is_saf0(surface)

        deformation = OrbitClosureDeformation(surface, old=self._surface)

        bindings = bindings.clone()
        bindings.forget(Surface)
        bindings.define(Surface, deformation)

        return bindings

    async def _consume(self, product, cost):
        r"""
        Enlarge the orbit closure from the cylinders in the decomposition ``product``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

        Run until we find the orbit closure, i.e., investigate in two directions::

            >>> import asyncio
            >>> asyncio.run(oc.resolve())
            [Ngon([1, 3, 5])] [OrbitClosure] dimension: 4/6
            [Ngon([1, 3, 5])] [OrbitClosure] dimension: 6/6
            [Ngon([1, 3, 5])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 6 in H_3(4) (ambient dimension 6) (dimension: 6) (dimension_upper_bound: 6) (directions: 2) (directions_with_cylinders: 2) (dense: True) (stratum: H_3(4))
            True

        TESTS:

        Check that the JSON output for this goal works::

            >>> from flatsurvey.reporting import Json

            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=report, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

            >>> import asyncio
            >>> asyncio.run(oc.resolve())
            True

            >>> asyncio.run(oc.report())
            >>> report.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 3, 5], "genus": 3, "type": "Ngon", "repr": "Ngon([1, 3, 5])"}, "orbit-closure": [{"timestamp": "...", "dimension": 6, "dimension_upper_bound": 6, "directions": 2, "directions_with_cylinders": 2, "dense": true, "stratum": "H_3(4)", "value": {"type": "GL2ROrbitClosure", "repr": "GL(2,R)-orbit closure of dimension at least 6 in H_3(4) (ambient dimension 6)"}}]}

        A case where an expansion happens::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> surface = Ngon((1, 3, 13))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None, stale_limit=1)

            >>> import asyncio
            >>> asyncio.run(oc.resolve())
            [Ngon([1, 3, 13])] [OrbitClosure] dimension: 9/17
            ...
            [Ngon([1, 3, 13])] [OrbitClosure] Found 1 directions with cylinders without a dimension increase since the last expansion. Will expand the search radius again.
            ...
            [Ngon([1, 3, 13])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 17 in H_8(12, 2) ... (dense: True) (stratum: H_8(12, 2))
            True

        A case where a deformation is requested::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> from flatsurvey.reporting import Log
            >>> bindings = Bindings()
            >>> invoke_subcommand(OrbitClosure.click, "--deform-limit=0", bindings=bindings)
            >>> invoke_subcommand(Log.click, "--output=-", bindings=bindings)
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "3", "-a", "7", bindings=bindings)
            >>> oc = OrbitClosure.create(bindings)

            >>> from flatsurvey.restart import Restart
            >>> import asyncio
            >>> try:
            ...     asyncio.run(oc.resolve())
            ... except Restart as e:
            ...     bindings = e.create_bindings(bindings)
            ...     oc = OrbitClosure.create(bindings)
            ...     asyncio.run(oc.resolve())
            [OrbitClosure] dimension: 6/11
            [OrbitClosure] Found 0 directions with cylinders without a dimension increase. Will attempt to deform the surface to improve the situation.
            ...
            [OrbitClosure] dimension: 2/11
            ...
            [OrbitClosure] GL(2,R)-orbit closure of dimension at least 11 in H_5(6, 2) ... (dense: True) (stratum: H_5(6, 2))
            True

        """
        del cost

        dimension_increase = self._consume_augment_orbit_closure(product)

        self._consume_update_statistics(
            self._saddle_connections._current, product, dimension_increase
        )

        if self.dense:
            await self.report()
            return "COMPLETED"

        if self._limit is not None and self._statistics.directions >= self._limit:
            await self.report()
            return "COMPLETED"

        if self._symmetries:
            if dimension_increase:
                self._saddle_connection_orientations.promote_symmetries()
            else:
                self._saddle_connection_orientations.demote_symmetries()

        if self._consume_should_expand():
            self._consume_expand()

        if self._consume_should_deform():
            from flatsurvey.restart import Restart

            raise Restart(self._deformation)

        return "NOT_COMPLETED"

    async def report(self, **kwargs):
        r"""
        Report our final verdict about this orbit closure.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Report, Json
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> report = Report([Json({Surface: surface}, output="-")])
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=report, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

            >>> import asyncio
            >>> asyncio.run(oc.report())

            >>> report.flush()
            {"surface": {...}, "orbit-closure": [{"timestamp": "...", "dimension": 2, ..., "dense": null, ...}}]}

        """
        if not self.reported():
            await self._report.result(
                self,
                self._orbit_closure(),
                dimension=self.dimension,
                dimension_upper_bound=self._surface.orbit_closure_dimension_upper_bound,
                directions=self._statistics.directions,
                directions_with_cylinders=self._statistics.directions_with_cylinders,
                dense=self.dense,
                stratum=str(self._orbit_closure().ambient_stratum()),
                **kwargs,
            )


class OrbitClosureDeformation(Deformation):
    @property
    def orbit_closure_dimension_upper_bound(self):
        r"""
        Return an upper bound for the dimension of the orbit closure.

        This is the same as the upper bound for the surface before deformation.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurf.geometry.pyflatsurf_conversion import from_pyflatsurf
            >>> from flatsurf import GL2ROrbitClosure

            >>> S = Ngon((1, 1, 1))

            >>> O = GL2ROrbitClosure(S.surface())

            >>> delta = [O.V2(v, 0).vector for v in O.lift(O.tangent_space_basis()[0])]
            >>> deformation = from_pyflatsurf((O._surface + delta).surface())

            >>> T = OrbitClosureDeformation(deformation, S)
            >>> T.orbit_closure_dimension_upper_bound
            2

        """
        return self._old.orbit_closure_dimension_upper_bound


__test__ = {
    # Work around https://trac.sagemath.org/ticket/33951
    "OrbitClosure._orbit_closure": OrbitClosure._orbit_closure.__doc__,
    "OrbitClosure.click": OrbitClosure.click.__doc__,
}
