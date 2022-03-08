r"""
Tests a conjecture by Boshernitzan in triangles.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "boshernitzan-conjecture", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker boshernitzan-conjecture [OPTIONS]
      Determines whether Boshernitzan's conjecture holds for a surface.
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
    Determines whether Boshernitzan's conjecture holds for a surface.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting.report import Report
        >>> from flatsurvey.cache import Cache
        >>> from flatsurvey.jobs import BoshernitzanConjecture, BoshernitzanConjectureOrientations, FlowDecompositions
        >>> surface = Ngon((1, 1, 1))
        >>> orientations = BoshernitzanConjectureOrientations(surface=surface)
        >>> BoshernitzanConjecture(report=Report([]), flow_decompositions=FlowDecompositions(surface=surface, saddle_connection_orientations=orientations, report=Report([])), saddle_connection_orientations=orientations, cache=Cache())
        boshernitzan-conjecture

    """

    @copy_args_to_internal_fields
    def __init__(
        self,
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

            >>> BoshernitzanConjecture.reduce([{'result': None}, {'result': None}])
            >>> BoshernitzanConjecture.reduce([{'result': None}, {'result': False}])
            False
            >>> BoshernitzanConjecture.reduce([{'result': None}, {'result': True}])
            True
            >>> BoshernitzanConjecture.reduce([{'result': False}, {'result': True}])
            Traceback (most recent call last):
            ...
            AssertionError

        """
        results = [result["result"] for result in results]

        assert not (
            any(result is True for result in results)
            and any(result is False for result in results)
        )

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
            >>> goal = BoshernitzanConjecture(report=Report([log]), flow_decompositions=FlowDecompositions(surface=surface, saddle_connection_orientations=orientations, report=Report([])), saddle_connection_orientations=orientations, cache=Cache())

        Investigate in a single direction::

            >>> import asyncio
            >>> produce = orientations.produce()
            >>> asyncio.run(produce)
            True

        Since we have not found any direction that is not cylinder periodic
        (since there are none), we cannot tell yet whether Boshernitzan's
        conjectures hold::

            >>> report = goal.report()
            >>> asyncio.run(report)
            [Ngon([1, 1, 1])] [BoshernitzanConjecture] ¯\_(ツ)_/¯

        If we try to investigate in another direction, we find that we have
        considered all possible directions::

            >>> produce = orientations.produce()
            >>> asyncio.run(produce)
            False

        So, we conclude that the Boshernitzan's conjecture holds for this
        surface::

            >>> asyncio.run(goal.report())
            [Ngon([1, 1, 1])] [BoshernitzanConjecture] True

        """
        if decomposition.minimalComponents():
            await self.report(False)
            return Goal.COMPLETED

        if decomposition.undeterminedComponents():
            await self.report(None)
            return Goal.COMPLETED

        assert all(component.cylinder() for component in decomposition.components())

        return not Goal.COMPLETED

    async def report(self, result=None, **kwargs):
        if self._resolved != Goal.COMPLETED:
            if result is None and self._saddle_connection_orientations.exhausted:
                result = True

            await self._report.result(
                self,
                result,
                **kwargs,
            )
