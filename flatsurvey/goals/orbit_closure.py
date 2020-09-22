r"""
Computes the GL_2(R) orbit closure of a surface

EXAMPLES::

    >>> from survey.objects.ngons import Ngon
    >>> from survey.services import Services
    >>> from survey.objects.surface import Surface
    >>> services = Services()
    >>> services.register(Surface, Ngon((1, 5, 10)))
    >>> o = OrbitClosure(services)
    >>> o.resolve()
    >>> o.result()
    GL(2,R)-orbit closure of dimension at least 8 in H_7(4^3, 0) (ambient dimension 17)

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

from pinject import copy_args_to_internal_fields

from .flow_decomposition import FlowDecompositions
from ..pipeline import Consumer
from ..util.click.group import GroupedCommand

class OrbitClosure(Consumer):
    @copy_args_to_internal_fields
    def __init__(self, surface, report, flow_decompositions):
        super().__init__(flow_decompositions)

    def command(self):
        return ["orbit-closure"]

    def _consume(self, decomposition, cost):
        orbit_closure = self._surface.orbit_closure()
        orbit_closure.update_tangent_space_from_flow_decomposition(decomposition)
        self._report.progress(self, "dimension", orbit_closure.dimension(), self._surface._bound)
        self._report.update(self, orbit_closure, dimension=orbit_closure.dimension(), dense=orbit_closure.dimension() == self._surface._bound or None)
        assert orbit_closure.dimension() <= self._surface._bound, "%s <= %s"%(orbit_closure.dimension(), self._surface._bound)
        if orbit_closure.dimension() == self._surface._bound:
            return Consumer.COMPLETED
        return not Consumer.COMPLETED

@click.command(name="orbit-closure", cls=GroupedCommand, group="Goals")
def orbit_closure():
    return OrbitClosure
