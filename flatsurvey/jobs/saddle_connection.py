from itertools import islice
from pinject import copy_args_to_internal_fields

from ..pipeline import Producer, Processor

class SaddleConnections(Producer):
    @copy_args_to_internal_fields
    def __init__(self, surface):
        super().__init__()

        self._connections = None

    def by_length(self):
        self.__connections = self._surface.orbit_closure()._surface.connections().byLength()
        self._connections = iter(self.__connections)

    def randomize(self, lower_bound):
        # TODO: Fix in flatsurf
        import cppyy
        cppyy.include("flatsurf/saddle_connections_sample.hpp")
        cppyy.include("flatsurf/saddle_connections_sample_iterator.hpp")
        self.__connections = self._surface.orbit_closure()._surface.connections().sample().lowerBound(lower_bound)
        self._connections = iter(self.__connections)

    def command(self):
        return ["saddle-connections"]

    def _produce(self):
        if self._connections is None:
            self.by_length()
        try:
            self._current = next(self._connections)
            # TODO: This seems to work around a bug with cppyy. Without this we get a "zero vector has no direction"
            str(self._current)
            return not Producer.EXHAUSTED
        except StopIteration:
            return Producer.EXHAUSTED


class SaddleConnectionOrientations(Processor):
    @copy_args_to_internal_fields
    def __init__(self, saddle_connections):
        super().__init__(producers=[saddle_connections])
        self._seen = None

    def command(self):
        return ["saddle-connection-orientations"]

    def _consume(self, connection, cost):
        vector = connection.vector()
        if self._seen == None:
            import cppyy
            self._seen = cppyy.gbl.std.set[type(vector), type(vector).CompareSlope]()

        if vector.x():
            try:
                vector = type(vector)(vector.x() / vector.x(), vector.y() / vector.x())
            except Exception: pass
        if vector.y():
            try:
                vector = type(vector)(vector.x() / vector.y(), vector.y() / vector.y())
            except Exception: pass


        import cppyy
        flat_triangulation = self._saddle_connections._surface.flat_triangulation()
        source = cppyy.gbl.flatsurf.Vertex.source(connection.source(), flat_triangulation.combinatorial())
        target = cppyy.gbl.flatsurf.Vertex.source(connection.target(), flat_triangulation.combinatorial())
        # if flat_triangulation.angle(source) == 1 or flat_triangulation.angle(target) == 1:
        #     print("Ignoring connection at marked point.")
        #     return not Processor.COMPLETED

        if self._seen.find(vector) == self._seen.end():
            self._seen.insert(vector)
            self._current = connection.vector()
            self._notify_consumers(cost)

        return not Processor.COMPLETED
