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
#        Copyright (C) 2020-2025 Julian Rüth
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

from abc import abstractmethod
from typing import Literal

import click

from flatsurvey.pipeline.goal import Goal


class Consumer(Goal):
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

    .. NOTE:

        While technically all consumers are a :class:`Goal` only the ones that
        make sense as the actual "goal" of a survey register themselves as
        goals in their ``click``.

    """

    DEFAULT_CACHE_ONLY = False

    _cache_only_option = click.option(
        "--cache-only",
        default=DEFAULT_CACHE_ONLY,
        is_flag=True,
        help="Do not perform any computation. Only query the cache.",
    )

    def __init__(
        self, producers, cache=None, cache_only=DEFAULT_CACHE_ONLY, report=None
    ):
        super().__init__()

        from flatsurvey.cache import Cache

        if cache is None:
            cache = Cache()

        if report is None:
            from flatsurvey.reporting import Report

            report = Report([])

        self._producers = producers
        self._cache: Cache = cache
        self._cache_only = cache_only
        self._report = report

        # Register ourselves with each produces so we get notified of any
        # objects they generate.
        for producer in producers:
            producer.register_consumer(self)

    async def resolve(self) -> bool:
        r"""
        Make our producers generate objects until this consumer marks itself as
        resolved. Return whether we could resolve or our producers were exhausted.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, OrbitClosure
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

            >>> import asyncio
            >>> resolve = oc.resolve()
            >>> asyncio.run(resolve)
            True

        """
        while not self._resolved:
            for producer in self._producers:
                if await producer.produce() != "EXHAUSTED":
                    break
            else:
                return False

            import asyncio

            await asyncio.sleep(0)

        return True

    async def consume_cache(self):
        r"""
        Process previous cached results for this goal.

        Subclasses can override this if they want to interact with cached results.
        """
        if self._cache_only:
            self._resolved = True

    async def consume(
        self, product, cost
    ) -> Literal["COMPLETED"] | Literal["NOT_COMPLETED"]:
        r"""
        Process the ``product`` by one of the producers we are attached to and
        return whether we are willing to consume further data or whether we
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
            >>> consume = orientations.consume(next(iter(surface.surface().pyflatsurf().codomain().flat_triangulation().connections())), cost=0)
            >>> asyncio.run(consume)
            'NOT_COMPLETED'

        Note that you should actually never call this explicitly. It gets
        called whenever a producer produces something new::

            >>> produce = connections.produce()
            >>> asyncio.run(produce)
            'NOT_EXHAUSTED'

        """
        assert not self._resolved

        self._resolved = await self._consume(product, cost) == "COMPLETED"

        return "COMPLETED" if self._resolved else "NOT_COMPLETED"

    @abstractmethod
    async def _consume(
        self, product, cost
    ) -> Literal["COMPLETED"] | Literal["NOT_COMPLETED"]:
        r"""
        Process the ``product`` by one of the producers we are attached to and
        return whether we are willing to consume further data or whether we
        have been completely resolved.

        Actual consumers must implement this method.
        """

    def reported(self):
        r"""
        Return whether this consumer has already reported results.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, OrbitClosure
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

            >>> oc.reported()
            False

            >>> import asyncio
            >>> report = oc.report()
            >>> asyncio.run(report)
            [Ngon([1, 3, 5])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_3(4) (ambient dimension 6) (dimension: 2) (dimension_upper_bound: 6) (directions: 0) (directions_with_cylinders: 0) (dense: None) (stratum: H_3(4))

            >>> oc.reported()
            True

        """
        return self in self._report._reported

    async def report(self):
        r"""
        Report the current state of this consumer to the reporter. Typically
        called at the very end to make sure that this consumer has reported its
        final verdict even if inconclusive.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, OrbitClosure
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> orientations = SaddleConnectionOrientations(connections)
            >>> log = Log({Surface: surface}, output="-")
            >>> flow_decompositions = FlowDecompositions(surface=surface, saddle_connection_orientations=orientations)
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections, saddle_connection_orientations=orientations, cache=None)

            >>> import asyncio
            >>> report = oc.report()
            >>> asyncio.run(report)
            [Ngon([1, 3, 5])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_3(4) (ambient dimension 6) (dimension: 2) (dimension_upper_bound: 6) (directions: 0) (directions_with_cylinders: 0) (dense: None) (stratum: H_3(4))

        """
