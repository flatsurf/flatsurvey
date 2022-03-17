r"""
Tests a conjecture by Boshernitzan in triangles.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "boshernitzan-conjecture", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker boshernitzan-conjecture [OPTIONS]
      Determines whether Conjecture 2.2 in Boshernitzan's *Billiards and Rational
      Periodic Directions in Polygons* holds for this surface.
    Options:
      --cache-only  Do not perform any computation. Only query the cache.
      --help        Show this message and exit.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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


class BoshernitzanConjecture(Goal):
    r"""
    Determines whether Conjecture 2.2 in Boshernitzan's *Billiards and Rational
    Periodic Directions in Polygons* holds for this surface.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting.report import Report
        >>> from flatsurvey.cache import Cache
        >>> from flatsurvey.jobs import BoshernitzanConjecture, BoshernitzanConjectureOrientations, FlowDecompositions
        >>> surface = Ngon((1, 1, 1))
        >>> orientations = BoshernitzanConjectureOrientations(surface=surface)
        >>> BoshernitzanConjecture(surface=surface, report=Report([]), flow_decompositions=FlowDecompositions(surface=surface, saddle_connection_orientations=orientations, report=Report([])), saddle_connection_orientations=orientations, cache=Cache())
        boshernitzan-conjecture

    """

    @copy_args_to_internal_fields
    def __init__(
        self,
        surface,
        flow_decompositions,
        saddle_connection_orientations,
        report,
        cache,
        cache_only=Goal.DEFAULT_CACHE_ONLY,
    ):
        from flatsurvey.jobs import BoshernitzanConjectureOrientations

        if not isinstance(
            saddle_connection_orientations, BoshernitzanConjectureOrientations
        ):
            raise TypeError(
                "must iterate over boshernitzan-conjecture-orientations to test Boshenitzan's conjecture"
            )

        super().__init__(
            producers=[flow_decompositions], cache=cache, cache_only=cache_only
        )

        self._verdict = {
            assertion: None for assertion in self._saddle_connection_orientations.assertions
        }

    async def consume_cache(self):
        r"""
        Try to resolve this goal from cached previous runs.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting.report import Report
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.jobs import BoshernitzanConjecture, BoshernitzanConjectureOrientations, FlowDecompositions
            >>> surface = Ngon((1, 1, 1))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)
            >>> goal = BoshernitzanConjecture(surface=surface, report=Report([]), flow_decompositions=FlowDecompositions(surface=surface, saddle_connection_orientations=orientations, report=Report([])), saddle_connection_orientations=orientations, cache=Cache())

        Try to resolve the goal from (no) cached results::

            >>> import asyncio
            >>> asyncio.run(goal.consume_cache())

            >>> goal.resolved
            False

        We mock some artificial results from previous runs and consume that
        artificial cache::

            >>> import asyncio
            >>> from unittest.mock import patch
            >>> from flatsurvey.cache.cache import Nothing
            >>> async def results(self):
            ...    yield {"data": {"assertion": "ignored", "result": None}}
            ...    yield {"data": {"assertion": "ignored", "result": True}}
            >>> with patch.object(Nothing, '__aiter__', results):
            ...    asyncio.run(goal.consume_cache())

            >>> goal.resolved
            True

        """
        for assertion in self._verdict:
            results = self._cache.results(
                surface=self._surface, job=self,
                filter=f'assertion: {{ equalTo: "{assertion}" }}'
            )

            verdict = await results.reduce()

            if verdict is not None or self._cache_only:
                self._verdict[assertion] = verdict

                await self._report_assertion(result=verdict, assertion=assertion, cached=True)

        if self._cache_only:
            self._resolved = Goal.COMPLETED

        if all([verdict is not None for (assertion, verdict) in self._verdict.items()]):
            self._resolved = Goal.COMPLETED

    @classmethod
    @click.command(
        name="boshernitzan-conjecture",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],
    )
    @Goal._cache_only_option
    def click(cache_only):
        return {
            "bindings": [
                PartialBindingSpec(BoshernitzanConjecture)(cache_only=cache_only)
            ],
            "goals": [BoshernitzanConjecture],
        }

    def command(self):
        command = ["boshernitzan-conjecture"]
        if self._cache_only != self.DEFAULT_CACHE_ONLY:
            command.append("--cache-only")
        return command

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return a final verdict.

        EXAMPLES::

            >>> BoshernitzanConjecture.reduce([{'assertion': 'ignored', 'result': None}, {'assertion': 'ignored', 'result': None}])
            >>> BoshernitzanConjecture.reduce([{'assertion': 'ignored', 'result': None}, {'assertion': 'ignored', 'result': False}])
            False
            >>> BoshernitzanConjecture.reduce([{'assertion': 'ignored', 'result': None}, {'assertion': 'ignored', 'result': True}])
            True
            >>> BoshernitzanConjecture.reduce([{'assertion': 'ignored', 'result': False}, {'assertion': 'ignored', 'result': True}])
            Traceback (most recent call last):
            ...
            ValueError: historic results are contradictory

        """
        if not results:
            return None

        assertion = results[0]["assertion"]
        if any(result["assertion"] != assertion for result in results):
            raise ValueError("cannot consolidate results relating to different conjectures")

        results = [result["result"] for result in results]

        if (any(result is True for result in results) and any(result is False for result in results)):
            raise ValueError("historic results are contradictory")

        if any(result is False for result in results):
            return False

        if any(result is True for result in results):
            return True

        return None

    async def _consume(self, decomposition, cost):
        r"""
        Determine whether ``decomposition`` supports Boshernitzan's conjectures.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.jobs import BoshernitzanConjecture, BoshernitzanConjectureOrientations, FlowDecompositions
            >>> surface = Ngon((1, 1, 1))
            >>> orientations = BoshernitzanConjectureOrientations(surface=surface)
            >>> log = Log(surface=surface)
            >>> goal = BoshernitzanConjecture(surface=surface, report=Report([log]), flow_decompositions=FlowDecompositions(surface=surface, saddle_connection_orientations=orientations, report=Report([])), saddle_connection_orientations=orientations, cache=Cache())

        We investigate all directions and conclude that Boshernitzan's
        conjecture holds for this triangle (note that we do not check the
        isosceles portion of conjecture (e) it is contained in the
        right-triangle portion when checking (1, 1, 2))::

            >>> import asyncio
            >>> asyncio.run(orientations.produce())
            True
            >>> asyncio.run(orientations.produce())
            True
            >>> asyncio.run(orientations.produce())
            False

            >>> asyncio.run(goal.report())
            [Ngon([1, 1, 1])] [BoshernitzanConjecture] True (assertion: b)
            [Ngon([1, 1, 1])] [BoshernitzanConjecture] True (assertion: c)

        """
        if decomposition.undeterminedComponents():
            for assertion, verdict in self._verdict.items():
                if verdict is None:
                    await self._report_assertion(result=None, assertion=assertion)
            return Goal.COMPLETED

        for assertion, verdict in self._verdict.items():
            if assertion == "b":
                d = sum(self._surface.angles)
                assert d % 2 == 1

                from flatsurvey.jobs import BoshernitzanConjectureOrientations
                pow = BoshernitzanConjectureOrientations._pow(self._saddle_connection_orientations._current, 2*d)
                if pow[0] > 0 and pow[1] == 0:
                    continue

            if decomposition.minimalComponents():
                assert verdict is not True

                if verdict is None:
                    self._verdict[assertion] = False
                    await self._report_assertion(result=False, assertion=assertion)

                continue

            assert all(component.cylinder() for component in decomposition.components())

        if all(verdict is not None for verdict in self._verdict.values()):
            return Goal.COMPLETED

        return not Goal.COMPLETED

    async def _report_assertion(self, assertion, result, **kwargs):
        await self._report.result(
            self,
            result,
            assertion=assertion,
            **kwargs,
        )

    async def report(self, result=None, **kwargs):
        if result is not None:
            raise NotImplementedError

        for assertion in self._verdict:
            if self._verdict[assertion] is None and self._saddle_connection_orientations.exhausted:
                await self._report_assertion(result=True, assertion=assertion, **kwargs)
