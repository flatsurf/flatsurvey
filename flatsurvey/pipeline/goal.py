r"""
A generic goal of a program run.

Invocations of flatsurvey run until all registered goals have been resolved.

EXAMPLES:

    >>> from flatsurvey.jobs import OrbitClosure
    >>> Goal in OrbitClosure.mro()
    True

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022-2025 Julian Rüth
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

from abc import ABC, abstractmethod


class Goal(ABC):
    def __init__(self):
        self._resolved = False

    @property
    def resolved(self):
        r"""
        Return whether this goal should be considered resolved, i.e., whether
        it has already reached a final verdict.

        EXAMPLES:

        Typically, a :class:`Transformation` does never reach the resolved
        status::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 1, 1))
            >>> connections = SaddleConnections(surface=surface)
            >>> orientations = SaddleConnectionOrientations(saddle_connections=connections)
            >>> orientations.resolved
            False

        """
        return self._resolved

    @abstractmethod
    async def resolve(self) -> bool:
        r"""
        Perform the steps necessary to satisfy this goal.

        Return whether the goal is actually resolved or it remained inconclusive.

        Concrete subclasses must implement this method.

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
