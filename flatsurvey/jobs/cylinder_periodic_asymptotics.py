r"""
Determines the growth rate of cylinder periodic decompositions.

Typically, you would want to determine the distribution of cylinder asymptotic
directions such that all circumferences are shorter than some `R`.  For this,
you should limit the length of saddle connections considered.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "cylinder-periodic-asymptotics", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker cylinder-periodic-asymptotics [OPTIONS]
    Determines the maximum circumference of all cylinders in each cylinder
    periodic direction.
    Options:
      --cache-only  Do not perform any computation. Only query the cache.
      --help        Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2021-2022 Julian Rüth
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


class CylinderPeriodicAsymptotics(Goal):
    r"""
    Determines the maximum circumference of all cylinders in each cylinder
    periodic direction.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting.report import Report
        >>> from flatsurvey.cache import Cache
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CylinderPeriodicAsymptotics(report=Report([]), flow_decompositions=flow_decompositions, cache=Cache())
        cylinder-periodic-asymptotics

    """

    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions, cache, cache_only=Goal.DEFAULT_CACHE_ONLY):
        super().__init__(producers=[flow_decompositions], cache=cache, cache_only=cache_only)

        self._results = []

    async def consume_cache(self):
        r"""
        Attempt to resolve this goal from previous cached runs.

        This produces a summary of previous run when --cache-only is set, otherwise, it does nothing.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting.report import Report
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.reporting.log import Log
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> cache = Cache()
            >>> log = Log(surface)
            >>> goal = CylinderPeriodicAsymptotics(report=Report([log]), flow_decompositions=flow_decompositions, cache=cache, cache_only=True)

        We mock some artificial results from previous runs::

            >>> from collections import namedtuple
            >>> from unittest.mock import MagicMock
            >>> async def nodes(self):
            ...    yield { "distribution": [ lambda: 1, lambda: 2 ] }
            ...    yield { "distribution": [ lambda: 2 ] }
            >>> cache.results = MagicMock()
            >>> cache.results.return_value.nodes.return_value.__aiter__ = nodes

        Now we can consume our artificial cache. Since we set ``cache_only`` above, it is reported immediately::

            >>> import asyncio
            >>> asyncio.run(goal.consume_cache())
            [Ngon([1, 1, 1])] [CylinderPeriodicAsymptotics] ¯\_(ツ)_/¯ (distributions: [[1, 2], [2]])

        """
        if not self._cache_only:
            return

        results = self._cache.results(surface=self._flow_decompositions._surface, job=self)

        distributions = [[d() for d in node["distribution"]] async for node in results.nodes()]

        # We do not merge the distributions into a single distribution since
        # they might be of unequal length and therefore the result distribution
        # would be skewed.
        await self._report.result(self, None, distributions=distributions)
        self._resolved = Goal.COMPLETED

    @classmethod
    @click.command(
        name="cylinder-periodic-asymptotics",
        cls=GroupedCommand,
        group="Goals",
        help=__doc__.split("EXAMPLES")[0],
    )
    @Goal._cache_only_option
    def click(cache_only):
        return {
            "bindings": [PartialBindingSpec(CylinderPeriodicAsymptotics)(cache_only=cache_only)],
            "goals": [CylinderPeriodicAsymptotics],
        }

    def command(self):
        command = ["cylinder-periodic-asymptotics"]
        if self._cache_only != self.DEFAULT_CACHE_ONLY:
            command.append("--cache-only")
        return command

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return the resulting distribution.
        """
        raise NotImplementedError("merging of distributions not implemented yet")

    async def _consume(self, decomposition, cost):
        r"""
        Record the circumference of the cylinders in `decomposition`.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.cache import Cache
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CylinderPeriodicAsymptotics(report=Report([log]), flow_decompositions=flow_decompositions, cache=Cache())

        Investigate in a single direction::

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            True

        ::

            >>> report = ccp.report()
            >>> asyncio.run(report)
            [Ngon([1, 1, 1])] [CylinderPeriodicAsymptotics] ¯\_(ツ)_/¯ (distribution: [6.92820323027551])

        """
        if decomposition.minimalComponents():
            self._results.append(False)
        elif decomposition.undeterminedComponents():
            self._results.append(None)
        else:
            # TODO: Is area() twice the area? See #8.
            def float_height(component):
                height = float(component.height())
                vertical = component.vertical().vertical()
                from math import sqrt

                scale = sqrt(float(vertical.x()) ** 2 + float(vertical.y()) ** 2)
                return height / scale

            self._results.append(
                max(float_height(component) for component in decomposition.components())
            )

        return not Goal.COMPLETED

    async def report(self, result=None, **kwargs):
        if self._resolved != Goal.COMPLETED:
            distribution = self._results

            undetermineds = len([r for r in distribution if r is None])
            if undetermineds:
                print(
                    f"warning: {undetermineds} undetermined components most likely minimal but might be very long cylinders."
                )
            distribution = sorted([r for r in distribution if r])

            await self._report.result(
                self,
                result,
                distribution=distribution,
            )
