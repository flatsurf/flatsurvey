from itertools import islice
from pinject import copy_args_to_internal_fields

from ..pipeline import Producer, Processor

class SaddleConnections(Producer):
    @copy_args_to_internal_fields
    def __init__(self, surface):
        super().__init__()

        self._connections = None

    def _produce(self):
        if self._connections is None:
          # TODO: make limit configurable
          import pyflatsurf
          # TODO: Remove once https://github.com/flatsurf/flatsurf/pull/208 has been merged
          import cppyy
          cppyy.include('flatsurf/saddle_connections_by_length.hpp')
          cppyy.include('flatsurf/saddle_connections_by_length_iterator.hpp')
          self.__connections = self._surface.orbit_closure()._surface.saddle_connections().byLength()
          self._connections = iter(self.__connections)
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
        super().__init__(saddle_connections)
        self._seen = []

    def _consume(self, connection, cost):
        x, y = connection.vector().x(), connection.vector().y()

        if not any([True for (xx, yy) in self._seen if xx * y == yy * x or xx * y == -yy * x]):
            self._seen.append((x, y))
            # print("Investigating in direction %s"%((x, y),))
            self._current = connection.vector()
            self._notify_consumers(cost)

        return not Processor.COMPLETED
