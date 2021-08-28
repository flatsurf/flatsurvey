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
      --help   Show this message and exit.

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2021 Julian Rüth
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
#*********************************************************************

import click

from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline import Consumer
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.pipeline.util import PartialBindingSpec

class CylinderPeriodicAsymptotics(Consumer):
    r"""
    Determines the maximum circumference of all cylinders in each cylinder
    periodic direction.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting.report import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CylinderPeriodicAsymptotics(report=Report([]), flow_decompositions=flow_decompositions)
        cylinder-periodic-asymptotics

    """
    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions):
        super().__init__(producers=[flow_decompositions])

        self._results = []

    @classmethod
    @click.command(name="cylinder-periodic-asymptotics", cls=GroupedCommand, group="Goals", help=__doc__.split('EXAMPLES')[0])
    def click():
        return {
            'bindings': [ PartialBindingSpec(CylinderPeriodicAsymptotics)() ],
            'goals': [ CylinderPeriodicAsymptotics ],
        }

    def command(self):
        return ["cylinder-periodic-asymptotics"]

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return the resulting distribution.

        EXAMPLES::

            >>> CylinderPeriodicAsymptotics.reduce([False, 2, 1])
            [1, 2]
            >>> CylinderPeriodicAsymptotics.reduce([None, 2, 1])
            warning: 1 undetermined components most likely minimal but might be very long cylinders.
            [1, 2]

        """
        undetermineds = len([r for r in results if r is None])
        if undetermineds:
            print(f"warning: {undetermineds} undetermined components most likely minimal but might be very long cylinders.")
        return sorted([r for r in results if r])

    async def _consume(self, decomposition, cost):
        r"""
        Record the circumference of the cylinders in `decomposition`.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CylinderPeriodicAsymptotics(report=Report([log]), flow_decompositions=flow_decompositions)

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
        if decomposition.decomposition.minimalComponents():
            self._results.append(False)
        elif decomposition.decomposition.undeterminedComponents():
            self._results.append(None)
        else:
            # TODO: Is area() twice the area? See #8.
            def float_height(component):
                height = float(component.height())
                vertical = component.vertical().vertical()
                from math import sqrt
                scale = sqrt(float(vertical.x())**2 + float(vertical.y())**2)
                return height / scale
            self._results.append(max(float_height(component) for component in decomposition.decomposition.components()))

        return not Consumer.COMPLETED

    async def report(self, result=None, **kwargs):
        if self._resolved != Consumer.COMPLETED:
            await self._report.result(self, result, distribution=CylinderPeriodicAsymptotics.reduce(self._results))
