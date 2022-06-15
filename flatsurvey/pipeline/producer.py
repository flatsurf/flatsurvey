r"""
An abstract part of a computation that generates data that is used in further computations.

EXAMPLES::

    >>> from flatsurvey.jobs import SaddleConnections
    >>> Producer in SaddleConnections.mro()
    True

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2021 Julian Rüth
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

import time


class Producer:
    r"""
    In the pipeline graph of jobs, any source of an edge is a Producer. So
    producers generate data that is the further processed by registered consumers.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface=surface)

        >>> isinstance(connections, Producer)
        True

    """
    EXHAUSTED = False

    def __init__(self):
        self._consumers = set()
        self._current = None
        self._exhausted = False

    async def produce(self):
        r"""
        Produce new data and notify all attached consumers of it. Return
        whether nothing more can be produced because this producer is
        exhausted.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)

            >>> import asyncio
            >>> produce = connections.produce()
            >>> asyncio.run(produce) != Producer.EXHAUSTED
            True

            >>> connections._current
            -3

        """
        start = time.perf_counter()
        if self._produce() == Producer.EXHAUSTED:
            self._exhausted = True
            return Producer.EXHAUSTED
        cost = time.perf_counter() - start

        await self._notify_consumers(cost)

        return not Producer.EXHAUSTED

    @property
    def exhausted(self):
        r"""
        Return whether this producer has been exhausted.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface, limit=0)

        For a producer to be exhausted, it has to be asked to :meth:`produce`
        at least once unsuccesfully. This is a bit unfortunate, but due to the
        lazy implementation, there is currently no other way::

            >>> import asyncio
            >>> asyncio.run(connections.produce())
            False

            >>> connections.exhausted
            True

        """
        return self._exhausted

    async def _notify_consumers(self, cost):
        r"""
        Notify all attached consumers that something new has been produced.
        """
        for consumer in list(self._consumers):
            from flatsurvey.pipeline.consumer import Consumer

            if await consumer.consume(self._current, cost) == Consumer.COMPLETED:
                self._consumers.remove(consumer)

    def register_consumer(self, consumer):
        r"""
        Register ``consumer`` so that it gets notified whenever something new
        is produced.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)

        Creating a consumer calls this method implicitly::

            >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)

            >>> connections._consumers
            {saddle-connection-orientations}

        """
        self._consumers.add(consumer)

    def _produce(self):
        r"""
        Produce something and return whether nothing new can be produced
        because we have been exhausted.

        Actual producers must implement this method.

        """
        raise NotImplementedError
