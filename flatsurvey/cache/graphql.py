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
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.pipeline.util import PartialBindingSpec

from pinject import copy_args_to_internal_fields

from flatsurvey.reporting import GraphQL as GraphQLReporter

class GraphQL:
    r"""
    A cache of previous results stored behind a GraphQL API in the cloud.

    EXAMPLES::

        >>> GraphQL()
        cache

    """
    @copy_args_to_internal_fields
    def __init__(self, endpoint=GraphQLReporter.DEFAULT_ENDPOINT, key=GraphQLReporter.DEFAULT_API_KEY, region=GraphQLReporter.DEFAULT_REGION):
        pass

    async def result_async(self, surface, job, exact=False):
        r"""
        Return the previous results for ``job`` on ``surface``.
        """
        camel = GraphQLReporter._camel(job)
        surfaces = await self.query_async(f"""
            query($name: String!) {{
                surfaces: allSurfaces(filter: {{
                    name: {{
                        equalTo: $name
                    }},
                    {camel}sBySurfaceExist: true, 
                }}) {{
                    nodes {{
                        id,
                        data,
                        results: {camel}sBySurface {{
                            nodes {{
                                id,
                                surface: surfaceBySurface {{
                                    id,
                                    data
                                }},
                                data
                            }}
                        }}
                    }}
                }}
            }}
        """, variable_values={
            "name": str(surface)
        })
        surfaces = Cache.resolve(surfaces, region=self._region)
        if exact:
            raise NotImplementedError("exact row filtering")
        from itertools import chain
        return CacheNodes(nodes=list(chain(*[surface["results"]["nodes"] for surface in surfaces["surfaces"]["nodes"]])), job=job, surface=surface)

    def _run(self, task):
        import threading
        import asyncio
        result = None
        exception = None
        def run():
            nonlocal result
            nonlocal exception
            try:
                result = asyncio.run(task)
            except Exception as e:
                exception = e
        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        if exception is not None:
            raise exception
        return result

    def result(self, surface, job, exact=False):
        r"""
        Return the previous results for ``job`` on ``surface``.
        """
        return self._run(self.result_async(surface=surface, job=job, exact=exact))

    @classmethod
    def resolve(cls, obj, region=GraphQLReporter.DEFAULT_REGION):
        r"""
        Restore pickles in ``obj``.

        Objects stored in the GraphQL database, might contain some pickled
        parts that are stored as binary blobs on S3. This method turns these
        pickles into callables that restore from S3 when needed.
        """
        if isinstance(obj, list):
            return [cls.resolve(o) for o in obj]
        if isinstance(obj, tuple):
            return tuple(cls.resolve(list(obj)))
        if isinstance(obj, dict):
            if 'pickle' in obj:
                restored = None
                url = obj['pickle']
                def restore():
                    nonlocal restored
                    if restored is None:
                        from zlib import decompress
                        from pickle import loads
                        from io import BytesIO
                        import boto3
                        s3 = boto3.client("s3", region_name=region)
                        prefix = 's3://'
                        assert url.startswith(prefix)
                        bucket, key = url[len(prefix):].split('/', 1)
                        with BytesIO() as buffer:
                            s3.download_fileobj(bucket, key, buffer)
                            buffer.seek(0)
                            pickle = decompress(buffer.read())
                            try:
                                restored = loads(pickle)
                            except Exception as e:
                                print(f"Failed to restore {obj}:\n{e}")
                    return restored
                restore.__doc__ = obj['description']
                return restore
            else:
                return {cls.resolve(key): cls.resolve(value) for (key, value) in obj.items()}

        return obj

    def _get(self, action, **kwargs):
        response = action(**kwargs)
        rows = response['Items']

        while response.get('LastEvaluatedKey'):
            response = action(**kwargs, ExclusiveStartKey=response['LastEvaluatedKey'])
            rows.extend(response['Items'])

        return rows

    def __repr__(self):
        return "cache"

    def query(self, query, *args, **kwargs):
        r"""
        Run the GraphQL ``query`` and return the result.
        """
        return self._run(self.query_async(query=query, *args, **kwargs))

    async def query_async(self, query, *args, **kwargs):
        r"""
        Run the GraphQL ``query`` and return the result.
        """
        if isinstance(query, str):
            from gql import gql
            query = gql(query)
        return await GraphQLReporter.graphql_client(endpoint=self._endpoint, key=self._key).execute_async(query, *args, **kwargs)

    @classmethod
    @click.command(name="cache", cls=GroupedCommand, group="Cache", help=__doc__.split('EXAMPLES')[0])
    @click.option("--endpoint", type=str, default=GraphQLReporter.DEFAULT_ENDPOINT, show_default=True, help="GraphQL HTTP endpoint to connect to")
    @click.option("--key", type=str, default=GraphQLReporter.DEFAULT_API_KEY, show_default=True, help="GraphQL API key")
    @click.option("--region", type=str, default=GraphQLReporter.DEFAULT_REGION, show_default=True, help="AWS region to connect to")
    def click(endpoint, key, region):
        return {
            'bindings': [ PartialBindingSpec(GraphQL, name="Cache")(endpoint=endpoint, key=key, region=region) ],
        }


class CacheNodes:
    r"""
    Rows returned from calls to ``GraphQL.result``.
    """
    def __init__(self, nodes, job, surface=None):
        self._nodes = nodes
        self._job = job
        self._surface = surface

    def nodes(self):
        r"""
        Return the nodes stored in the GraphQL database for these results.

        Use ``results`` for a more condensed version that is stripped of
        additional metadata.
        """
        return [
            {
                **node['data'],
                'surface': node['surface']['data']
            } for node in self._nodes
        ]

    def results(self):
        r"""
        Return the objects that were registered as previous results in the
        database.
        """
        return [
            node['data']['result']() for node in self._nodes
        ]

    def reduce(self):
        r"""
        Combine all results to an overall verdict.

        Return ``None`` if the results are inconclusive.
        """
        return self._job.reduce([node['data'] for node in self._nodes])

