r"""
Determines whether a surface decomposes completely into cylinders in some direction.

Naturally, this can only be decided partially, i.e., we can say, "yes", there
is such a direction but we can never say "no" _all_ directions have a
non-cylinder.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "cylinder-periodic-direction", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker cylinder-periodic-direction [OPTIONS]
      Determines whether there is a direction for which the surface decomposes
      into cylinders.
    Options:
      --limit INTEGER  stop search after having looked at that many flow
                       decompositions  [default: no limit]
      --help           Show this message and exit.

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
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

class CylinderPeriodicDirection(Consumer):
    r"""
    Determines whether there is a direction for which the surface decomposes
    into cylinders.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> CylinderPeriodicDirection(report=Report([]), flow_decompositions=flow_decompositions)
        cylinder-periodic-direction

    """
    DEFAULT_LIMIT = None

    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions, limit=DEFAULT_LIMIT):
        super().__init__(producers=[flow_decompositions])

        self._directions = 0

    @classmethod
    @click.command(name="cylinder-periodic-direction", cls=GroupedCommand, group="Goals", help=__doc__.split('EXAMPLES')[0])
    @click.option("--limit", type=int, default=DEFAULT_LIMIT, help="stop search after having looked at that many flow decompositions  [default: no limit]")
    def click(limit):
        return {
            'bindings': [ PartialBindingSpec(CylinderPeriodicDirection)(limit=limit) ],
            'goals': [ CylinderPeriodicDirection ],
        }

    def command(self):
        command = ["cylinder-periodic-direction"]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        return command

    def _consume(self, decomposition, cost):
        r"""
        Determine wheter ``decomposition`` is cylinder periodic.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnections, SaddleConnectionOrientations
            >>> surface = Ngon((1, 1, 1))
            >>> log = Log(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> cpd = CylinderPeriodicDirection(report=Report([log]), flow_decompositions=flow_decompositions)
        
        Investigate in a single direction. We find that this direction is
        cylinder periodic::

            >>> flow_decompositions.produce()
            [Ngon((1, 1, 1))] [CylinderPeriodicDirection] True (directions: 1)
            True

        """
        self._directions += 1

        if all([component.cylinder() == True for component in decomposition.decomposition.components()]):
            self.report(True, decomposition=decomposition)
            return Consumer.COMPLETED

        if self._directions >= limit:
            self.report()
            return Consumer.COMPLETED

        return not Consumer.COMPLETED

    def report(self, result=None, **kwargs):
        if self._resolved != Consumer.COMPLETED:
            self._report.result(self, result, directions=self._directions)
