from .service import Service

class SaddleConnectionOrientations(Service):
    def __init__(self, services):
        super().__init__(services)
        self._connections = self._get(SaddleConnections)
        self._seen = []

    def advance(self):
        return self._connections.advance()

    def consume(self):
        connection = self._connections.current
        x, y = connection.vector().x(), connection.vector().y()
        if any([True for (xx, yy) in self._seen if xx * y == yy * x or xx * y == -yy * x]):
            return None
        self._seen.append((x, y))
        # print("Investigating in direction %s"%((x, y),))
        self.current = connection.vector()
        self._notify()

class SaddleConnections(Service):
    def __init__(self, services):
        super().__init__(services)

        from ..sources.surface import Surface
        self.surface = services.get(Surface)
        self._connections = None

    def advance(self):
        if self._connections is None:
            # TODO: make limit configurable
            import pyflatsurf
            self._connections = iter(self.surface.orbit_closure()._surface.saddle_connections(pyflatsurf.flatsurf.Bound(2, 0)))
        try:
            self.current = next(self._connections)
            self._notify()
            return True
        except StopIteration:
            return False
