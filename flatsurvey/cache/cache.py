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
        Return the nodes stored in the GraphQL database for these results.

        Use ``results`` for a more condensed version that is stripped of
        additional metadata.

        TODO
        """
        async for node in self:
            yield {
                **node["data"],
                "surface": node["surface"]["data"],
                "timestamp": node["timestamp"],
            }

    async def results(self):
        r"""
        Return the objects that were registered as previous results in the
        database.

        TODO
        """
        async for node in self:
            result = node["data"]["result"]
            if result is not None:
                result = node["data"]["result"]()
                if result is not None:  # TODO: why is this needed? See #7.
                    # TODO: We should not use _nodes here.
                    setattr(result, "erase", lambda: self._nodes.erase(node))
                    yield result

    async def reduce(self):
        r"""
        Combine all results to an overall verdict.

        Return ``None`` if the results are inconclusive.

        TODO
        """
        return self._job.reduce([node["data"] async for node in self])


class Nothing(Results):
    r"""
    A missing cached result.

    TODO
    """

    async def __aiter__(self):
        r"""
        TODO
        """
        for i in ():
            yield i
