r"""
An abstract part of a computation that is fed data to compute something and
passes that data on to the next consumer in the pipeline.

EXAMPLES:

Any step of a computation that converts data implements the Processor
interface, e.g., FlowDecompositions turn saddle connections into flow
decompositions::

    >>> from flatsurvey.jobs import FlowDecompositions
    >>> Processor in FlowDecompositions.mro()
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

from flatsurvey.pipeline.consumer import Consumer
from flatsurvey.pipeline.producer import Producer


class Processor(Producer, Consumer):
    r"""
    A processor is simply a producer and a consumer at the same time.

    Implementing classes only have to implement ``_consume`` which must set
    `_current` to the newly produced object.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface=surface)
        >>> isinstance(connections, Processor)
        False
        >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)
        >>> isinstance(orientations, Processor)
        True

    """

    def __init__(self, producers):
        Producer.__init__(self)
        Consumer.__init__(self, producers=producers)

        self._produced = False

    async def produce(self):
        r"""
        Ask our producers to produce until our own ``consume`` gets called so
        we actually produce. Return whether all our producers have been
        exhausted in the process.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)
            >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)

            >>> import asyncio
            >>> produce = orientations.produce()
            >>> asyncio.run(produce) != Producer.EXHAUSTED
            True

            >>> orientations._current
            (6, (-2*c ~ -3.4641016))

        """
        self._current = None

        # Currently, we do not have processors with multiple sources. When we
        # have, we might need a better strategy here.
        while self._current is None:
            for source in self._producers:
                if await source.produce() != Producer.EXHAUSTED:
                    break
            else:
                return Producer.EXHAUSTED

        return not Producer.EXHAUSTED
