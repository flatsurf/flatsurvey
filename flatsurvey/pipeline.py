r"""
Base classes for a processing pipeline that is process by a worker.

TODO
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

import sys
import pinject
import time

class Producer:
    def __init__(self):
        self._consumers = set()
        self._current = None

    EXHAUSTED = False

    def produce(self):
        r"""

        Return whether something has been produced.
        """
        start = time.perf_counter()
        if self._produce() == Producer.EXHAUSTED:
            return Producer.EXHAUSTED
        end = time.perf_counter()

        self._notify_consumers(end - start)

        return not Producer.EXHAUSTED

    def _notify_consumers(self, cost):
        for consumer in list(self._consumers):
            if consumer.consume(self._current, cost) == Consumer.COMPLETED:
                self._consumers.remove(consumer)

    def register_consumer(self, consumer):
        self._consumers.add(consumer)

    def _produce(self):
        r"""

        Return whether something has been produced.
        """
        raise NotImplementedError

    def __repr__(self): return type(self).__name__


class Consumer:
    def __init__(self, *producers):
        self._producers = producers
        self._resolved = not Consumer.COMPLETED
        for producer in producers:
            producer.register_consumer(self)

    COMPLETED = False

    def consume(self, product, cost):
        r"""

        Return whether more data can be consumed.
        """
        assert self._resolved != Consumer.COMPLETED
        self._resolved = self._consume(product, cost)
        return self._resolved

    def _consume(self, product, cost):
        r"""


        Return whether more data can be consumed.
        """
        raise NotImplementedError

    def resolve(self):
        r"""


        Return whether the goal was resolved successfully.
        """
        while self._resolved != Consumer.COMPLETED:
            for producer in self._producers:
                if producer.produce() != Producer.EXHAUSTED:
                    break
            else:
                return not Consumer.COMPLETED

        return Consumer.COMPLETED

    def __repr__(self): return type(self).__name__

    def key(self): return repr(self)


class Processor(Producer, Consumer):
    def __init__(self, *producers):
        Producer.__init__(self)
        Consumer.__init__(self, *producers)

    def produce(self):
        for source in self._producers:
            if source.produce() != Producer.EXHAUSTED:
                return not Producer.EXHAUSTED

        return Producer.EXHAUSTED


def provide(name, factory):
    class Binding(pinject.BindingSpec):
        provide = pinject.provides(name)(lambda self: factory())

    return Binding()


def bind(*args, **kwargs):
    class Binding(pinject.BindingSpec):
        def configure(self, bind):
            bind(*args, **kwargs)
    return Binding()


def graph(*bindings):
    modules = [module for (name, module) in sys.modules.items() if name.startswith('flatsurvey')]
    return pinject.new_object_graph(modules=modules, binding_specs=bindings)
