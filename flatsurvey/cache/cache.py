r"""
Access cached results from previous runs.

Currently, the only cache we support is a GraphQL/S3 database. It would be
fairly trivial to change that and allow for other similar systems as well.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "cache", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker cache [OPTIONS]
      A cache of previous results stored behind a GraphQL API in the cloud.
    Options:
      --endpoint TEXT  GraphQL HTTP endpoint to connect to  [default:
                       https://m1by93q54i.execute-api.eu-
                       central-1.amazonaws.com/dev/]
      --key TEXT       GraphQL API key  [default:
                       ZLonPeaT0M71epvWLGNbua2XMA6wQOiq5HHfO72I]
      --region TEXT    AWS region to connect to  [default: eu-central-1]
      --help           Show this message and exit.

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


class Cache:
    r"""
    A cache that does actually *not* do any caching.

    This is the default cache that is used when the user did not ask for an
    actual cache explicitly on the command line.
    """

    def results(self, job, surface=None, exact=False):
        r"""
        Return our previous verdicts on running ``job`` for ``surface``.

        EXAMPLES:

        Since this cache does not actually cache anything, it always returns
        ``None``::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> results = Cache().results(surface=Ngon([1,1,1]), job=CompletelyCylinderPeriodic)

            >>> import asyncio
            >>> asyncio.run(results.reduce()) is None
            True

        """
        return Nothing(job=job)


class Results:
    r"""
    Base class for cached results.

    Subclasses should implement ``__aiter__`` to yield these cached results.

    EXAMPLES::

        >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
        >>> cache = Cache()
        >>> results = cache.results(job=CompletelyCylinderPeriodic)

        >>> isinstance(results, Results)
        True

    """

    def __init__(self, job):
        self._job = job

    async def nodes(self):
        r"""
        Return the nodes stored in the cache for these results.

        Use :meth:`results` for a more condensed version that is stripped of
        additional metadata.

        EXAMPLES:

        We query the nodes of some mock cached data::

            >>> cache = Cache()

            >>> async def results(self):
            ...    yield {"data": {"result": None}, "surface": {"data": {}}, "timestamp": None}

            >>> from unittest.mock import patch
            >>> from flatsurvey.cache.cache import Nothing
            >>> with patch.object(Nothing, '__aiter__', results):
            ...    from flatsurvey.jobs import CompletelyCylinderPeriodic
            ...    results = cache.results(job=CompletelyCylinderPeriodic)
            ...    async def to_list(generator): return [item async for item in generator]
            ...    import asyncio
            ...    asyncio.run(to_list(results.nodes()))
            [{'result': None, 'surface': {}, 'timestamp': None}]

        """
        async for node in self:
            yield {
                **node["data"],
                "surface": node["surface"]["data"],
                "timestamp": node["timestamp"],
            }

    async def results(self):
        r"""
        Return the objects that were registered as previous results.

        EXAAMPLES:

        We query the nodes of some mock cached data::

            >>> cache = Cache()

            >>> async def results(self):
            ...    yield {"data": {"result": None}, "surface": {"data": {}}, "timestamp": None}

            >>> from unittest.mock import patch
            >>> from flatsurvey.cache.cache import Nothing
            >>> with patch.object(Nothing, '__aiter__', results):
            ...    from flatsurvey.jobs import CompletelyCylinderPeriodic
            ...    results = cache.results(job=CompletelyCylinderPeriodic)
            ...    async def to_list(generator): return [item async for item in generator]
            ...    import asyncio
            ...    asyncio.run(to_list(results.results()))
            [None]

        """
        async for node in self:
            result = node["data"]["result"]
            if callable(result):
                result = result()
            yield result

    async def reduce(self):
        r"""
        Combine all results to an overall verdict.

        Return ``None`` if the results are inconclusive.

        EXAAMPLES:

        We query the nodes of some mock cached data::

            >>> cache = Cache()

            >>> async def results(self):
            ...    yield {"data": {"result": False, "surface": {"data": {}}, "timestamp": None}}

            >>> from unittest.mock import patch
            >>> from flatsurvey.cache.cache import Nothing
            >>> with patch.object(Nothing, '__aiter__', results):
            ...    from flatsurvey.jobs import CompletelyCylinderPeriodic
            ...    results = cache.results(job=CompletelyCylinderPeriodic)
            ...    import asyncio
            ...    asyncio.run(results.reduce())
            False

        """
        return self._job.reduce([node["data"] async for node in self])


class Nothing(Results):
    r"""
    A missing cached result.

    EXAMPLES::

        >>> cache = Cache()

        >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
        >>> isinstance(cache.results(job=CompletelyCylinderPeriodic), Nothing)
        True

    """

    async def __aiter__(self):
        r"""
        Return an asynchrononous iterator over no results.
        """
        for i in ():
            yield i
