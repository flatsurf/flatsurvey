r"""
Flow decompositions of a flat triangulation into cylinders and minimal components.


"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click
import time

from pinject import copy_args_to_internal_fields

from .saddle_connection import SaddleConnectionOrientations
from ..util.click.group import GroupedCommand

from ..pipeline import Processor, Consumer

class FlowDecompositions(Processor):
    @copy_args_to_internal_fields
    def __init__(self, surface, report, saddle_connection_orientations):
        super().__init__(saddle_connection_orientations)

    def consume(self, orientation, cost):
        # TODO: Make limit configurable
        start = time.perf_counter()
        self._current = self._surface.orbit_closure().decomposition(orientation, 64)
        end = time.perf_counter()
        # TODO: Fails because cppyythonizations only want to serialize default constructibles
        # self._report.partial(self, self._current, orientation=orientation)
        self._notify_consumers(cost + end - start)
        return True


class CompletelyCylinderPeriodic(Consumer):
    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions):
        super().__init__(flow_decompositions)

    def command(self):
        return ["completely-cylinder-periodic"]

    def _consume(self, decomposition, cost):
        if any([component.cylinder() == False for component in decomposition.decomposition.components()]):
            self._report.update(self, False, decomposition=decomposition)
            return Consumer.COMPLETED
        return not Consumer.COMPLETED


class CylinderPeriodicDirection(Consumer):
    @copy_args_to_internal_fields
    def __init__(self, report, flow_decompositions):
        super().__init__(flow_decompositions)

    def command(self):
        return ["cylinder-periodic-direction"]

    def _consume(self, decomposition, cost):
        if all([component.cylinder() == True for component in decomposition.decomposition.components()]):
            # TODO: cppyythonizations cannot serialize non default constructibles
            self._report.update(self, True) #, decomposition=decomposition)
            return Consumer.COMPLETED
        return not Consumer.COMPLETED


@click.command(name="completely-cylinder-periodic", cls=GroupedCommand, group="Goals")
def completely_cylinder_periodic():
    return CompletelyCylinderPeriodic
    

@click.command(name="cylinder-periodic-direction", cls=GroupedCommand, group="Goals")
def cylinder_periodic_direction():
    return CylinderPeriodicDirection
