r"""
An abstract part of a computation that is fed data to compute something.

EXAMPLES:

Any goal of a computation implements the Consumer interface::

    >>> from flatsurvey.jobs import OrbitClosure
    >>> Consumer in OrbitClosure.mro()
    True

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2022 Julian Rüth
#
#  flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
# *********************************************************************


class Consumer:
    r"""
    In the pipeline graph of jobs, anything that an edge points to is a
    Consumer. So consumers take in intermediate results that come out of a
    Producer, e.g., OrbitClosure consumes the decompositions that come out of
    FlowDecompositions. FlowDecompositions is itself a Consumer (and a
    Producer) which consumes directions of saddle connections.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface=surface)
        >>> isinstance(connections, Consumer)
        False
        >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)
        >>> isinstance(orientations, Consumer)
        True

    Each consumer registers to one (or several) ``producers``. Whenever these
    produces generate something new, the consumers ``consume`` method is
    called::

        >>> orientations._producers
        [saddle-connections]

    """
    COMPLETED = False

    def __init__(self, producers):
        self._producers = producers

        # Some consumers can be resolved, e.g., when we are sure that we
        # determined the correct orbit closure, we'd set its _resolved to
        # COMPLETED.
        self._resolved = not Consumer.COMPLETED

        # Register ourselves with each produces so we get notified of any
        # objects they generate.
        for producer in producers:
            producer.register_consumer(self)

    async def consume(self, product, cost):
        r"""
        Process the ``product`` by one of the producers we are attached to and
        return whether we are willing to consumer further data or whether we
        have been completely resolved.

        The ``cost`` is the amount of time it took to generate that product;
        this can be used to determine whether things should be cached for
        example.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)
            >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)

            >>> import asyncio
            >>> consume = orientations.consume(next(iter(surface.flat_triangulation().connections())), cost=0)
            >>> asyncio.run(consume)
            True

        Note that you should actually never call this explicitly. It gets
        called whenever a producer produces something new::

            >>> produce = connections.produce()
            >>> asyncio.run(produce)
            True

        """
        assert self._resolved != Consumer.COMPLETED

        self._resolved = await self._consume(product, cost)

        return self._resolved

    async def _consume(self, product, cost):
        r"""
        Process the ``product`` by one of the producers we are attached to and
        return whether we are willing to consumer further data or whether we
        have been completely resolved.

        Actual consumers must implement this method.
        """
        raise NotImplementedError

    async def resolve(self):
        r"""
        Make our producers generate objects until this consumer marks itself as
        resolved. Return whether we could resolve or our producers were exhausted.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, OrbitClosure
            >>> from flatsurvey.cache import Cache
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
            >>> oc = OrbitClosure(surface=surface, report=Report([]), flow_decompositions=flow_decompositions, saddle_connections=connections, cache=Cache())

            >>> import asyncio
            >>> resolve = oc.resolve()
            >>> asyncio.run(resolve) == Consumer.COMPLETED
            True

        """
        while self._resolved != Consumer.COMPLETED:
            for producer in self._producers:
                from flatsurvey.pipeline.producer import Producer

                if await producer.produce() != Producer.EXHAUSTED:
                    break
            else:
                return not Consumer.COMPLETED

        return Consumer.COMPLETED

    def command(self):
        r"""
        Return the command line that can be used to create this consumer.

        Actual consumers must implement this method.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)
            >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)
            >>> orientations.command()
            ['saddle-connection-orientations']

        """
        raise NotImplementedError

    def __repr__(self):
        return " ".join(self.command())

    async def report(self):
        r"""
        Report the current state of this consumer to the reporter. Typically
        called at the very end to make sure that this consumer has reported its
        final verdict even if inconclusive.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, OrbitClosure
            >>> from flatsurvey.cache import Cache
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> log = Log(surface=surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, cache=Cache())

            >>> import asyncio
            >>> report = oc.report()
            >>> asyncio.run(report)
            [Ngon([1, 3, 5])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_3(4) (ambient dimension 6) (dimension: 2) (directions: 0) (directions_with_cylinders: 0) (dense: None)

        """
        pass
