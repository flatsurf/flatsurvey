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
#*********************************************************************
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
#*********************************************************************

class Cache:
    r"""
    A cache that does actually *not* do any caching.

    This is the default cache that is used when the user did not ask for an
    actual cache explicitly on the command line.
    """
    def results(self, surface, job, exact=False):
        r"""
        Return our previous verdicts on running ``job`` for ``surface``.

        EXAMPLES:

        Since this cache does not actually cache anything, it always returns
        ``None``::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> results = Cache().results(Ngon([1,1,1]), CompletelyCylinderPeriodic)
            >>> results.reduce() is None
            True
            
        """
        return Nothing()

class Nothing:
    r"""
    A missing cached result.
    """
    async def reduce(self):
        r"""
        Return a verdict from the found cached results or ``None`` if no result
        could be determined.

        Always returns ``None`` because we do not have any results cached here.
        """
        return None
