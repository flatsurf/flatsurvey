r"""
Computes the GL_2(R) orbit closure of a surface

EXAMPLES::

    >>> from survey.sources.ngons import Ngon
    >>> from survey.services import Services
    >>> from survey.sources.surface import Surface
    >>> services = Services()
    >>> services.register(Surface, Ngon((1, 5, 10)))
    >>> o = OrbitClosure(services)
    >>> o.resolve()
    >>> o.result()
    GL(2,R)-orbit closure of dimension at least 8 in H_7(4^3, 0) (ambient dimension 17)

"""
#*********************************************************************
#  This file is part of flatsurf.
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
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************
import click

from .flow_decomposition import FlowDecompositions
from .service import Service

class OrbitClosure(Service):
    def __init__(self, services):
        super().__init__(services)
        from ..sources.surface import Surface
        self.surface = services.get(Surface)
        self.complete = False
        self._decompositions = self._get(FlowDecompositions)

    def command(self):
        return ["orbit-closure"]

    def result(self):
        return self.surface.orbit_closure()

    def resolve(self):
        while not self.complete and self._decompositions.advance():
            pass

    def consume(self):
        if self.complete: return
        decomposition = self._decompositions.current
        o = self.surface.orbit_closure()
        o.update_tangent_space_from_flow_decomposition(decomposition)
        if o.dimension() == self.surface.ambient_stratum().dimension():
            self.complete = True

@click.command(name="orbit-closure")
def orbit_closure():
    return OrbitClosure
