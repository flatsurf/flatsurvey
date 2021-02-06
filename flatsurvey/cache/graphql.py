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

def _run(task):
    r"""
    Run ``task`` on a separate thread and block until it is complete.
    """
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

class GraphQL:
    r"""
    A cache of previous results stored behind a GraphQL API in the cloud.

    EXAMPLES::

        >>> GraphQL()
        cache

    """
    @copy_args_to_internal_fields
    def __init__(self, endpoint=GraphQLReporter.DEFAULT_ENDPOINT, key=GraphQLReporter.DEFAULT_API_KEY, region=GraphQLReporter.DEFAULT_REGION):
        self._pickle_cache = PickleCache(region=region)
        self._graphql_connection_pool = pool(lambda: GraphQLReporter.graphql_client(endpoint=self._endpoint, key=self._key))

    def results(self, job, surface=None, filter=None, exact=False, page_size=16):
        r"""
        Return the previous results for ``job`` on ``surface``.
        """
        if exact:
            raise NotImplementedError("exact surface filtering")

        query = lambda after: self._create_query(job=job, surface_filter=surface, result_filter=filter)

        return Results(job=job, nodes=Nodes(query=query, connection=self._graphql_connection_pool), pickle_cache=self._pickle_cache)

    def __repr__(self):
        return "cache"

    def _create_query(self, job, surface_filter=None, result_filter=None, limit=None, after=None):
        camel = GraphQLReporter._camel(job)
        upper = GraphQLReporter._upper(job)

        if surface_filter is None:
            surface_filter = ''
        else:
            surface_filter = f"""
            surfaceBySurface: {{
                { surface_filter }
            }}"""

        if result_filter is None:
            result_filter = ''

        filter = ""
        if surface_filter or result_filter:
            filter = f"""filter: {{
                { surface_filter }
                { result_filter }
            }}"""

        if limit is not None:
            filter = f"""{filter} first: {limit} orderBy: TIMESTAMP_DESC"""

        if after is not None:
            filter = f"""{filter} after: "{after}" """

        if filter:
            filter = f"({filter})"

        return f"""
            query {{
                results: all{upper}s{filter} {{
                    edges {{
                        cursor,
                        node {{
                            id
                            timestamp
                            data
                            surface: surfaceBySurface {{
                                id
                                data
                            }}
                        }}
                    }}
                }}
            }}"""


    @classmethod
    @click.command(name="cache", cls=GroupedCommand, group="Cache", help=__doc__.split('EXAMPLES')[0])
    @click.option("--endpoint", type=str, default=GraphQLReporter.DEFAULT_ENDPOINT, show_default=True, help="GraphQL HTTP endpoint to connect to")
    @click.option("--key", type=str, default=GraphQLReporter.DEFAULT_API_KEY, show_default=True, help="GraphQL API key")
    @click.option("--region", type=str, default=GraphQLReporter.DEFAULT_REGION, show_default=True, help="AWS region to connect to")
    def click(endpoint, key, region):
        return {
            'bindings': GraphQL.bindings(endpoint=endpoint, key=key, region=region),
        }

    @classmethod
    def bindings(cls, endpoint, key, region):
        return [ PartialBindingSpec(GraphQL, name="cache")(endpoint=endpoint, key=key, region=region) ]

    def deform(self, deformation):
        return {
            'bindings': GraphQL.bindings(endpoint=self._endpoint, key=self._key, region=self._region)
        }


class Nodes:
    r"""
    A (internally paginated) list of raw nodes as returned by a GraphQL ``query``.
    """
    def __init__(self, query, connection):
        self._make_query = query
        self._connection = connection

    def __iter__(self):
        after = None
        while True:
            results = _run(self._query(self._make_query(after)))['results']

            if len(results) == 0:
                break

            for edge in results['edges']:
                after = edge['cursor']
                node = edge['node']
                yield node

    async def _query(self, query, *args, **kwargs):
        r"""
        Run the GraphQL ``query`` and return the result.
        """
        from gql.transport.exceptions import TransportProtocolError
        if isinstance(query, str):
            from gql import gql
            query = gql(query)
        try:
            with self._connection() as connection:
                return await connection.execute_async(query, *args, **kwargs)
        except TransportProtocolError as e:
            from graphql import print_ast
            raise Exception(f"Query failed: {print_ast(query)}")


class Results:
    def __init__(self, job, nodes, pickle_cache):
        self._job = job
        self._pickle_cache = pickle_cache
        self._nodes = nodes

    def __iter__(self):
        for node in self._nodes:
            yield self._resolve(node)

    def nodes(self):
        r"""
        Return the nodes stored in the GraphQL database for these results.

        Use ``results`` for a more condensed version that is stripped of
        additional metadata.
        """
        for node in self:
            yield {
                **node['data'],
                'surface': node['surface']['data'],
                'timestamp': node['timestamp'],
            }

    def results(self):
        r"""
        Return the objects that were registered as previous results in the
        database.
        """
        for node in self:
            result = node['data']['result']
            if result is not None:
                yield node['data']['result']()

    def reduce(self):
        r"""
        Combine all results to an overall verdict.

        Return ``None`` if the results are inconclusive.
        """
        return self._job.reduce([node for node in self])

    def _resolve(self, obj):
        r"""
        Restore pickles in ``obj``.

        Objects stored in the GraphQL database, might contain some pickled
        parts that are stored as binary blobs on S3. This method turns these
        pickles into callables that restore from S3 when needed.
        """
        if isinstance(obj, list):
            return [self._resolve(o) for o in obj]
        if isinstance(obj, tuple):
            return tuple(self._resolve(list(obj)))
        if isinstance(obj, dict):
            if 'timestamp' in obj:
                import dateutil.parser
                obj['timestamp'] = dateutil.parser.isoparse(obj['timestamp'])
            if 'pickle' in obj:
                restored = None
                url = obj['pickle']
                def restore():
                    nonlocal restored
                    if restored is None:
                        restored = self._pickle_cache[url]
                    return restored
                restore.__doc__ = obj['description']
                restore.download = lambda: self._pickle_cache.download(url)
                return restore
            else:
                return {self._resolve(key): self._resolve(value) for (key, value) in obj.items()}

        return obj


class S3Cache:
    def __init__(self, region):
        self._downloads = {}
        self._s3_client_pool = pool(lambda: GraphQLReporter.s3_client(region=region))

    def __getitem__(self, url):
        self.download(url)
        ret = self._downloads[url]
        del self._downloads[url]
        return ret

    def schedule(self, url):
        pass

    def download(self, url):
        from io import BytesIO
        if url not in self._downloads:
            with self._s3_client_pool() as s3:
                prefix = 's3://'
                assert url.startswith(prefix)
                bucket, key = url[len(prefix):].split('/', 1)
                buffer = self._downloads[url] = BytesIO()
                s3.download_fileobj(bucket, key, buffer)
                buffer.seek(0)


class PickleCache:
    def __init__(self, region):
        self._cache = {}
        self._downloads = S3Cache(region=region)

    def __getitem__(self, url):
        if url in self._cache:
            cached = self._cache[url]()
            if cached is None:
                del self._cache[url]
            else:
                return cached

        import weakref
        from zlib import decompress
        from pickle import loads
        buffer = self._downloads[url]
        pickle = decompress(buffer.read())
        try:
            cached = loads(pickle)
            self._cache[url] = weakref.ref(cached)
            return cached
        except Exception as e:
            print(f"Failed to restore {url}:\n{e}")

    def _download(self, url):
        self._downloads.schedule(url)
            

def pool(constructor):
    import queue
    import contextlib

    pool = queue.Queue()

    @contextlib.contextmanager
    def connect(constructor=constructor, pool=pool):
        try:
            connection = pool.get(block=False)
        except queue.Empty:
            connection = constructor()
        yield connection
        pool.put(connection)
    return connect
