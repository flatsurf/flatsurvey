r"""
Computes the GL₂(R) orbit closure of a surface.

Naturally, this will only find a lower bound for the orbit closure, i.e., the
space it finds might be too small because not enough directions have been
investigated that would lead us to the full space.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "orbit-closure", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker orbit-closure [OPTIONS]
      Determines the GL₂(R) orbit closure of ``surface``.
    Options:
      --limit INTEGER         abort search after processing that many flow
                              decompositions with cylinders without an increase in
                              dimension  [default: 32]
      --expansions INTEGER    when the --limit has been reached, restart the search
                              with random saddle connections that are twice as long
                              as the ones used previously; repeat this doubling
                              process EXPANSIONS many times  [default: 4]
      --deform / --no-deform  When set, we deform the input surface as soon as we
                              found a third dimension in the tangent space and
                              restart. This is often beneficial if the input surface
                              has lots of symmetries and also when the Boshernitzan
                              criterion can rarely be applied due to SAF=0.
      --cache-only            Do not perform any computation. Only query the cache.
      --help                  Show this message and exit.

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


class OrbitClosure(Goal, Command):
    r"""
    Determines the GL₂(R) orbit closure of ``surface``.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(connections))
        >>> OrbitClosure(surface=surface, report=None, flow_decompositions=flow_decompositions, saddle_connections=connections, cache=None)
        orbit-closure

    """
    DEFAULT_LIMIT = 32
    DEFAULT_EXPANSIONS = 4
    DEFAULT_DEFORM = False

    @copy_args_to_internal_fields
    def __init__(
        self,
        surface,
        report,
        flow_decompositions,
        saddle_connections,
        cache,
        limit=DEFAULT_LIMIT,
        expansions=DEFAULT_EXPANSIONS,
        deform=DEFAULT_DEFORM,
        cache_only=Goal.DEFAULT_CACHE_ONLY,
    ):
        super().__init__(
            producers=[flow_decompositions], report=report, cache=cache, cache_only=cache_only
        )

        self._cylinders_without_increase = 0
        self._directions_with_cylinders = 0
        self._directions = 0
        self._expansions_performed = 0
        self._deformed = not deform

        import pyflatsurf

        self._lower_bound = pyflatsurf.flatsurf.Bound(0)
        self._upper_bound = pyflatsurf.flatsurf.Bound(0)

    async def consume_cache(self):
        r"""
        Try to resolve this goal from cached previous runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> from flatsurvey.cache import Cache
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(connections))
            >>> make_goal = lambda cache: OrbitClosure(surface=surface, report=None, flow_decompositions=flow_decompositions, saddle_connections=connections, cache=cache)

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> goal = make_goal(None)
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> from io import StringIO
            >>> goal = make_goal(Cache(jsons=[StringIO(
            ... '''{"orbit-closure": [{
            ...   "surface": {
            ...     "type": "Ngon",
            ...     "angles": [1, 1, 1]
            ...   },
            ...   "dense": null
            ... }, {
            ...   "surface": {
            ...     "type": "Ngon",
            ...     "angles": [1, 1, 1]
            ...   },
            ...   "dense": true
            ... }]}''')], pickles=None, report=None))
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        """
        with self._cache.defaults({"dense": None}):
            results = self._cache.get(self, self._surface.cache_predicate(False, cache=self._cache))

            verdict = self.reduce(results)

        if verdict is not None or self._cache_only:
            # TODO: Test JSON output.
            await self._report.result(self, result=None, dense=verdict, cached=True)
            self._resolved = Goal.COMPLETED

    @classmethod
    @click.command(
        name="orbit-closure",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        show_default=True,
        help="abort search after processing that many flow decompositions with cylinders without an increase in dimension",
    )
    @click.option(
        "--expansions",
        type=int,
        default=DEFAULT_EXPANSIONS,
        show_default=True,
        help="when the --limit has been reached, restart the search with random saddle connections that are twice as long as the ones used previously; repeat this doubling process EXPANSIONS many times",
    )
    @click.option(
        "--deform/--no-deform",
        default=DEFAULT_DEFORM,
        help="When set, we deform the input surface as soon as we found a third dimension in the tangent space and restart. This is often beneficial if the input surface has lots of symmetries and also when the Boshernitzan criterion can rarely be applied due to SAF=0.",
    )
    @Goal._cache_only_option
    def click(limit, expansions, deform, cache_only):
        return {
            "goals": [OrbitClosure],
            "bindings": OrbitClosure.bindings(
                limit=limit, expansions=expansions, deform=deform, cache_only=cache_only
            ),
        }

    @classmethod
    def bindings(cls, limit, expansions, deform, cache_only):
        return [
            PartialBindingSpec(OrbitClosure)(
                limit=limit, expansions=expansions, deform=deform, cache_only=cache_only
            )
        ]

    def deform(self, deformation):
        return {
            "goals": [OrbitClosure],
            "bindings": OrbitClosure.bindings(
                limit=self._limit,
                expansions=self._expansions,
                deform=False,
                cache_only=self._cache_only,
            ),
        }

    def command(self):
        command = [self.name()]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        if self._expansions != self.DEFAULT_EXPANSIONS:
            command.append(f"--expansions={self._expansions}")
        if self._deform != self.DEFAULT_DEFORM:
            command.append("--deform")
        if self._cache_only != self.DEFAULT_CACHE_ONLY:
            command.append("--cache-only")
        return command

    @property
    def dimension(self):
        return self._surface.orbit_closure().dimension()

    @property
    def dense(self):
        if self.dimension == self._surface.orbit_closure_dimension_upper_bound:
            return True

        return None

    async def _consume(self, decomposition, cost):
        r"""
        Enlarge the orbit closure from the cylinders in ``decomposition``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> log = Log(surface=surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(connections))
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, cache=None)

        Run until we find the orbit closure, i.e., investigate in two directions::

            >>> import asyncio
            >>> resolve = oc.resolve()
            >>> assert asyncio.run(resolve) == Goal.COMPLETED
            [Ngon([1, 3, 5])] [OrbitClosure] dimension: 4/6
            [Ngon([1, 3, 5])] [OrbitClosure] dimension: 6/6
            [Ngon([1, 3, 5])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 6 in H_3(4) (ambient dimension 6) (dimension: 6) (directions: 2) (directions_with_cylinders: 2) (dense: True)

        """
        self._directions += 1

        import pyflatsurf

        self._upper_bound = max(
            pyflatsurf.flatsurf.Bound.upper(self._saddle_connections._current.vector()),
            self._upper_bound,
        )

        if decomposition.cylinders() and not decomposition.undeterminedComponents():
            self._cylinders_without_increase += 1
            self._directions_with_cylinders += 1

        orbit_closure = self._surface.orbit_closure()
        dimension = self.dimension

        orbit_closure.update_tangent_space_from_flow_decomposition(decomposition)

        self._report.progress(
            source=self,
            what="dimension",
            count=self.dimension,
            total=self._surface.orbit_closure_dimension_upper_bound,
        )

        assert (
            self.dimension
            <= self._surface.orbit_closure_dimension_upper_bound
        ), "%s <= %s" % (
            self.dimension,
            self._surface.orbit_closure_dimension_upper_bound,
        )

        if dimension != self.dimension:
            self._cylinders_without_increase = 0

        if (
            self.dimension
            == self._surface.orbit_closure_dimension_upper_bound
        ):
            await self.report()
            return Goal.COMPLETED

        if self._cylinders_without_increase >= self._limit:
            await self.report()

            if self._expansions_performed < self._expansions:
                self._expansions_performed += 1

                self._report.log(self, "Found too many cylinders without improvements.")

                if self._lower_bound == 0:
                    self._lower_bound = self._upper_bound
                else:
                    self._lower_bound *= 4

                if self._upper_bound > self._lower_bound:
                    self._report.log(
                        self,
                        "Continuing search since connections seem to be increasing in length quickly.",
                    )
                else:
                    self._saddle_connections.randomize(self._lower_bound)
                    self._report.log(
                        self,
                        f"Now considering directions coming from saddle connections of length more than {self._lower_bound}",
                    )
                self._cylinders_without_increase = 0
                return not Goal.COMPLETED

            return Goal.COMPLETED

        if (
            dimension != self.dimension
            and not self._deformed
            and self.dimension > 3
        ):
            tangents = [
                orbit_closure.lift(v) for v in orbit_closure.tangent_space_basis()[2:]
            ]
            tangents = [sum(t for t in tangents)]

            def upper_bound(v):
                length = sum(abs(x.parent().number_field(x)) for x in v) / len(v)

                n = 1
                while n < length:
                    n *= 2
                return n

            tangents.sort(key=upper_bound)

            scale = 2
            while True:
                eligibles = False

                for tangent in tangents:
                    import cppyy

                    # What is a good vector to use to deform? See #3.
                    # n = upper_bound(tangent) * scale
                    n = upper_bound(tangent) // 4

                    # What is a good bound here? See #3.
                    # if n > 1e20:
                    #     print("Cannot deform. Deformation would lead to too much coefficient blowup.")
                    #     continue

                    eligibles = True

                    deformation = [
                        orbit_closure.V2(x / n, x / (2 * n)).vector for x in tangent
                    ]
                    try:
                        # Valid deformations that require lots of flips take forever. It's crucial to pick n such that no/very few flips are sufficient. See #3.
                        deformed = orbit_closure._surface + deformation

                        self._report.log(
                            self,
                            f"Deformed surface with {1/n} * tangent vector {tangent}.",
                        )

                        surface = deformed.surface()
                        from flatsurf.geometry.pyflatsurf_conversion import (
                            from_pyflatsurf,
                        )

                        surface = from_pyflatsurf(surface)

                        self._deformed = True

                        self._report.log(
                            self,
                            "Restarting OrbitClosure search with deformed surface.",
                        )

                        from flatsurvey.surfaces import Deformation

                        raise Deformation.Restart(surface, old=self._surface)
                    except cppyy.gbl.std.invalid_argument:
                        # TODO: Report progress.
                        continue

                scale *= 2

                if not eligibles:
                    import logging
                    # TODO: Report as progress?
                    logging.error("Cannot deform. No tangent vector can be used to deform.")
                    break

        return not Goal.COMPLETED

    @classmethod
    def reduce(cls, results):
        r"""
        Given a list of historic results, return a final verdict.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> from io import StringIO
            >>> cache = Cache(jsons=[StringIO(
            ... '''{"orbit-closure": [{
            ...   "dense": null
            ... }, {
            ...   "dense": null
            ... }]}''')], pickles=None, report=None)
            >>> OrbitClosure.reduce(cache.get("orbit-closure")) is None
            True

        ::

            >>> cache = Cache(jsons=[StringIO(
            ... '''{"orbit-closure": [{
            ...   "dense": null
            ... }, {
            ...   "dense": true
            ... }]}''')], pickles=None, report=None)
            >>> OrbitClosure.reduce(cache.get("orbit-closure")) is True
            True

        """
        results = [result.dense for result in results]
        assert not any([result is False for result in results])
        return True if any(result for result in results) else None

    async def report(self):
        if self._resolved != Goal.COMPLETED:
            orbit_closure = self._surface.orbit_closure()
            # TODO: Test JSON output.
            await self._report.result(
                self,
                orbit_closure,
                dimension=self.dimension,
                directions=self._directions,
                directions_with_cylinders=self._directions_with_cylinders,
                dense=self.dense,
            )
