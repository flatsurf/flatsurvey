import click

from .saddle_connection import SaddleConnectionOrientations
from .service import Service

class FlowDecompositions(Service):
    def __init__(self, services):
        super().__init__(services)

        from ..sources.surface import Surface
        self.surface = services.get(Surface)

        self._orientations = self._get(SaddleConnectionOrientations)

    def advance(self):
        return self._orientations.advance()

    def consume(self):
        # TODO: Make limit configurable
        self.current = self.surface.orbit_closure().decomposition(self._orientations.current, 64)
        self._notify()

class CompletelyCylinderPeriodic(Service):
    def __init__(self, services):
        super().__init__(services)
        self.complete = False
        self._decompositions = self._get(FlowDecompositions)

    def command(self):
        return ["completely-cylinder-periodic"]

    def resolve(self):
        while not self.complete and self._decompositions.advance():
            pass

    def consume(self):
        if self.complete: return
        decomposition = self._decompositions.current
        if any([componnt.cylinder() == False for component in decomposition.decomposition.components()]):
            self.complete = True
            self.result = False

class CylinderPeriodicDirection(Service):
    def __init__(self, services):
        super().__init__(services)
        self.complete = False
        self._decompositions = self._get(FlowDecompositions)

    def command(self):
        return ["cylinder-periodic-direction"]

    def resolve(self):
        while not self.complete and self._decompositions.advance():
            pass

    def consume(self):
        if self.complete: return
        decomposition = self._decompositions.current
        print(decomposition)
        if all([component.cylinder() == True for component in decomposition.decomposition.components()]):
            self.complete = True
            self.result = True

@click.command(name="completely-cylinder-periodic")
def completely_cylinder_periodic():
    return CompletelyCylinderPeriodic
    
@click.command(name="cylinder-periodic-direction")
def cylinder_periodic_direction():
    return CylinderPeriodicDirection
