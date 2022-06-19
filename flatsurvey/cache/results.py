r"""
Results from a :class:`Cache`.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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

from pinject import copy_args_to_internal_fields


class Results:
    r"""
    Results from a cache.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
        >>> from flatsurvey.cache import Cache
        >>> surface = Ngon((1, 1, 1))
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

        >>> goal = CompletelyCylinderPeriodic(report=None, flow_decompositions=flow_decompositions, cache=None)

        >>> from io import StringIO
        >>> cache = Cache(jsons=[StringIO('{"completely-cylinder-periodic": [{"result": null}, {"result": false}]}')], pickles=None)

        >>> results = cache.results(goal, predicate=lambda entry: True)

    TESTS::

        >>> isinstance(results, Results)
        True

    """
    @copy_args_to_internal_fields
    def __init__(self, job, results, cache):
        pass

    def __repr__(self):
        return repr(list(self))

    async def reduce(self):
        r"""
        Return a verdict for the job from this set of results.

        EXAMPLES:

        We provide a cache with some previous results, one inconclusive, one
        negative::

            >>> from io import StringIO
            >>> from flatsurvey.cache import Cache
            >>> cache = Cache(jsons=[StringIO('{"completely-cylinder-periodic": [{"result": null}, {"result": false}]}')], pickles=None)

            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> results = cache.results(CompletelyCylinderPeriodic, predicate=lambda entry: True)

        Since we had found that the surface is not completely cylinder periodic
        previously, we return that verdict::

            >>> import asyncio
            >>> asyncio.run(results.reduce())
            False

        """
        return self._job.reduce(self)

    def __iter__(self):
        from flatsurvey.cache.node import Node
        return iter(Node(result, cache=self._cache, kind=self._job.name()) for result in self._results)

    def __len__(self):
        return len(self._results)
