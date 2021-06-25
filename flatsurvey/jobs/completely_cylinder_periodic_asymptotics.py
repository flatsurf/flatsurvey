r"""
Determines the growth rate of completely cylinder asymptotic decompositions.

Typically, you would want to see the distribution of completely cylinder
asymptotic directions such that all circumferences are shorter than some `R`.
For this, you should limit the length of saddle connections considered.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "completely-cylinder-periodic-asymptotic", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker completely-cylinder-periodic-asymptotic [OPTIONS]

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2021 Julian Rüth
#
#  Flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurvey is distributed in the hope that it will be useful,
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

class CompletelyCylinderPeriodicAsymptotics(Consumer):
    r"""
    Determine the maximum circumference of all cylinders of length at most `R`
    in each completely cylinder periodic direction.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting.report import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CompletelyCylinderPeriodicAsymptotics(report=Report([]), flow_decompositions=flow_decompositions)
        completely-cylinder-periodic

    """
    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions):
        super().__init__(producers=[flow_decompositions])

        self._results = []

    @classmethod
    @click.command(name="completely-cylinder-periodic-asymptotics", cls=GroupedCommand, group="Goals", help=__doc__.split('EXAMPLES')[0])
    def click():
        return {
            'bindings': [ PartialBindingSpec(CompletelyCylinderPeriodicAsymptotics)() ],
            'goals': [ CompletelyCylinderPeriodicAsymptotics ],
        }

    def command(self):
        return ["completely-cylinder-periodic-asymptotics"]

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return the resulting distribution.

        EXAMPLES::

            >>> CompletelyCylinderPeriodic.reduce([False, 2, 1])
            [1, 2]
            >>> CompletelyCylinderPeriodic.reduce([None, 2, 1])
            warning: 1 undetermined component most likely minimal but might be a very long cylinder.
            [1, 2]

        """
        return sorted([r for r in results if r])

    def _consume(self, decomposition, cost):
        r"""
        Determine the maximum length of the cylinders.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodicAsymptotics(report=Report([log]), flow_decompositions=flow_decompositions)

        Investigate in a single direction::

            >>> flow_decompositions.produce()
            True

        TODO: Explain result

            >>> ccp.report()
            [Ngon([1, 1, 1])] [CompletelyCylinderPeriodic] ¯\_(ツ)_/¯ (cylinder_periodic_directions: 1) (undetermined_directions: 0)

        """
        if decomposition.decomposition.minimalComponents():
            self._results.append(False)
        elif decomposition.decomposition.undeterminedComponents():
            self._results.append(None)
        else:
            # TODO: Is area() twice the area?
            def float_height(component):
                height = float(component.height())
                vertical = component.vertical().vertical()
                from math import sqrt
                scale = sqrt(float(vertical.x())**2 + float(vertical.y())**2)
                return height / scale
            self._results.append(max(float_height(component) for component in decomposition.decomposition.components()))

        return not Consumer.COMPLETED

    def report(self, result=None, **kwargs):
        if self._resolved != Consumer.COMPLETED:
            self._report.result(self, result, distribution=CompletelyCylinderPeriodicAsymptotics.reduce(self._results))
