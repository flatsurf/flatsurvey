r"""
Reports results to a GraphQL API.

For writing access the environment variables FLATSURVEY_GRAPHQL_LOGIN and
FLATSURVEY_GRAPHQL_PASSWORD must be set. Also AWS credentials must be
configured, likely in .aws/credentials.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "graphql", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker graphql [OPTIONS]
      Reports results to our GraphQL cloud database.
    Options:
      --endpoint TEXT  GraphQL HTTP endpoint to connect to  [default:
                       https://m1by93q54i.execute-api.eu-
                       central-1.amazonaws.com/dev/]
      --key TEXT       GraphQL API key  [default:
                       ZLonPeaT0M71epvWLGNbua2XMA6wQOiq5HHfO72I]
      --region TEXT    AWS region to connect to  [default: eu-central-1]
      --bucket TEXT    S3 bucket to write to  [default: flatsurvey]
      --help           Show this message and exit.

Note that throughout the doctests here, we mock GraphQL and S3 so we do not
actually write to the real AWS.

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

from pinject import copy_args_to_internal_fields

from sage.misc.cachefunc import cached_method

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.pipeline.util import PartialBindingSpec

class GraphQL(Reporter):
    r"""
    Reports results to our GraphQL cloud database.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> GraphQL(surface=surface, lot=1337)
        graphql

    """
    DEFAULT_API_KEY = "ZLonPeaT0M71epvWLGNbua2XMA6wQOiq5HHfO72I"
    DEFAULT_ENDPOINT = "https://m1by93q54i.execute-api.eu-central-1.amazonaws.com/dev/"
    DEFAULT_REGION = "eu-central-1"
    DEFAULT_BUCKET = "flatsurvey"

    @copy_args_to_internal_fields
    def __init__(self, surface, lot, endpoint=DEFAULT_ENDPOINT, key=DEFAULT_API_KEY, bucket=DEFAULT_BUCKET, region=DEFAULT_REGION):
        pass

    @cached_method
    def _s3(self):
        s3 = GraphQL.s3_client(self._region)
        if not any(b['Name'] == self._bucket for b in s3.list_buckets()['Buckets']):
            s3.create_bucket(Bucket=self._bucket, CreateBucketConfiguration={"LocationConstraint": self._region})
        return s3

    @classmethod
    def s3_client(cls, region=DEFAULT_REGION):
        import boto3
        return boto3.client("s3", region_name=region)

    @cached_method
    def _graphql(self, readonly=False):
        if readonly:
            return GraphQL.graphql_client(endpoint=self._endpoint, key=self._key)
        else:
            import os
            return GraphQL.graphql_client(endpoint=self._endpoint, key=self._key, login=os.environ.get('FLATSURVEY_GRAPHQL_LOGIN'), password=os.environ.get('FLATSURVEY_GRAPHQL_PASSWORD'))

    @classmethod
    def graphql_client(cls, endpoint, key, login=None, password=None):
        from gql import AIOHTTPTransport, gql, Client
        import os.path
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.graphql")) as source:
            schema = source.read()
        if login is None or password is None:
            transport = AIOHTTPTransport(url=endpoint, headers={
                'x-api-key': key})
            client = Client(transport=transport, schema=schema)

            retry = 5
            while retry:
                import concurrent.futures
                try:
                    from flatsurvey.cache.graphql import GraphQL
                    GraphQL._run(client.execute_async(gql(r"query { __typename }")))
                    break
                except concurrent.futures.TimeoutError:
                    retry -= 1
                    if not retry: raise
                    print("Query timed out...retrying")
        else:
            client = cls.graphql_client(endpoint=endpoint, key=key)
            authorization = client.execute(gql(r"""
                mutation($mail: String!, $password: String!) {
                    signin(input: {mail:$mail, password:$password}){
                        jwtToken
                    }
                }"""), variable_values={
                "mail": login,
                "password": password,
            })['signin']['jwtToken']
            transport = AIOHTTPTransport(url=endpoint, headers={
                'x-api-key': key,
                'Authorization': f"Bearer {authorization}"})
            client = Client(transport=transport, schema=schema)
        client.execute_timeout = 60
        return client

    # TODO: Turn these things into a proper GraphQL wrapper that handles all the typical exceptions.
    def _execute(self, query, readonly=True, **kwargs):
        import concurrent.futures
        from gql.transport.exceptions import TransportQueryError, TransportServerError
        from gql import gql
        retry = 5
        while retry:
            retry -= 1
            client = self._graphql(readonly=readonly)
            try:
                return client.execute(gql(query), **kwargs)
            except concurrent.futures.TimeoutError:
                if retry == 0: raise
            except TransportQueryError:
                if retry == 0: raise
            except TransportServerError:
                if retry == 0: raise

            print("Query failed. Retrying.")

            self._graphql.clear_cache()

    @cached_method
    def _surface_id(self):
        return self._execute(r"""
            mutation($data: JSON!) {
                createSurface(input: {
                    surface: {
                        data: $data
                    }
                }) {
                    surface { id }
                }
            }""", readonly=False, variable_values={"data": self._serialize(self._surface)})["createSurface"]["surface"]["id"]

    def s3(self, raw, directory="pickles"):
        r"""
        Write the ``raw`` pickle string to an S3 bucket and return its URL.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        We use a mock for S3 in this example so we do not actually talk to AWS::

            >>> from pickle import dumps
            >>> from moto import mock_s3
            >>> with mock_s3():
            ...     log = GraphQL(surface=surface, lot=1337)
            ...     url = log.s3(dumps(surface))
            ...     # When we write the surface again to S3, nothing is actually stored:
            ...     assert log.s3(dumps(surface)) == url
            
            >>> url
            's3://flatsurvey/pickles/3cf75b5beabe3cb719441891d22ebe8fe1abd41a2c81bc1b023461aa5e5b5141.pickle.gz'

        """
        from zlib import compress
        import io
        import hashlib
        from botocore.exceptions import ClientError

        sha = hashlib.sha256()
        sha.update(raw)
        key = f"{directory}/{sha.hexdigest()}.pickle.gz"

        try:
            self._s3().head_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            if int(e.response['Error']['Code']) != 404:
                raise

            compressed = io.BytesIO()
            compressed.write(compress(raw))
            compressed.seek(0);

            self._s3().put_object(ACL='public-read', Body=compressed, Key=key, Bucket=self._bucket)

        return f"s3://{self._bucket}/{key}"

    def _serialize(self, item):
        r"""
        Return a serialized version of ``item`` that can be stored in a JSON dictionary.

        Note that types can augment this by implementing a method `_flatsurvey_characteristics`.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        We use a mock in this example so we do not actually talk to AWS::

            >>> from moto import mock_s3
            >>> with mock_s3():
            ...     log = GraphQL(surface=surface, lot=1337)
            ...     assert log._serialize(1) == 1
            ...     assert log._serialize(False) == False
            ...     assert log._serialize("abc") == "abc"
            ...     assert log._serialize([1, 2]) == [1, 2]
            ...     assert log._serialize(surface) == {
            ...         "angles": [1, 1, 1],
            ...         "description": "Ngon([1, 1, 1])",
            ...         "pickle": "s3://flatsurvey/Ngon/3cf75b5beabe3cb719441891d22ebe8fe1abd41a2c81bc1b023461aa5e5b5141.pickle.gz"
            ...     }, log._serialize(surface)

        """
        if type(item).__name__ == 'Integer':
            return int(item)

        if isinstance(item, (bool, str, int)):
            return item

        if isinstance(item, (list, tuple)):
            return [self._serialize(entry) for entry in item]

        characteristics = item._flatsurvey_characteristics() if hasattr(item, "_flatsurvey_characteristics") else {}

        from pickle import dumps
        try:
            dump = dumps(item)
        except Exception as e:
            return {
                **characteristics,
                "description": str(item),
                "error": str(e),
            }

        return {
            **characteristics,
            "description": str(item),
            "pickle": self.s3(dump, directory=GraphQL._upper(item)),
        };

    @classmethod
    def _upper(cls, job):
        r"""
        Write the name of a job in UpperCase.

        EXAMPLES::

            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> GraphQL._upper(CompletelyCylinderPeriodic)
            'CompletelyCylinderPeriodic'

        """
        if not isinstance(job, type):
            job = type(job)
        return job.__name__.strip('s')

    @classmethod
    def _camel(cls, job):
        r"""
        Write the name of a job in camelCase.

        EXAMPLES::

            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> GraphQL._camel(CompletelyCylinderPeriodic)
            'completelyCylinderPeriodic'

        """
        upper = cls._upper(job)
        return upper[0].lower() + upper[1:]

    @classmethod
    def _snake(cls, job):
        r"""
        Write the name of a job in snake_case.

        EXAMPLES::

            >>> from flatsurvey.jobs import CompletelyCylinderPeriodic
            >>> GraphQL._snake(CompletelyCylinderPeriodic)
            'completely_cylinder_periodic'

        """
        if not isinstance(job, type):
            job = type(job)
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', job.__name__).lower()

    def result(self, job, result, **kwargs):
        r"""
        Write the ``result`` of ``job`` to the database.

        EXAMPLES::

            >>> from flatsurvey.reporting.report import Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.cache import Cache

            >>> surface = Ngon((1, 1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=Report([]), flow_decompositions=flow_decompositions)

        We use a mock for GraphQL/S3 in this example so we do not actually talk
        to AWS::

            >>> from moto import mock_s3
            >>> from aioresponses import aioresponses
            >>> with mock_s3():
            ...     with aioresponses() as mock:
            ...         log = GraphQL(surface=surface, lot=1337)
            ...         # We log that a run to resolve ccp has been inconclusive and get that result back from the cache.
            ...         mock.post('https://m1by93q54i.execute-api.eu-central-1.amazonaws.com/dev/', payload={"data":{"createSurface":{"surface":{"id":"1337"}}}})
            ...         mock.post('https://m1by93q54i.execute-api.eu-central-1.amazonaws.com/dev/', payload={"data":{}})
            ...         log.result(job=ccp, result=None)
            ...         mock.post('https://m1by93q54i.execute-api.eu-central-1.amazonaws.com/dev/', payload={"data":{"surfaces": {"nodes": []}}})
            ...         assert Cache().results(surface=surface, job=ccp).reduce() == None, "expected unconclusive result"

        """
        import sys
        argv = sys.argv
        if argv and argv[0] == "-m": argv = argv[1:]

        self._execute(f"""
            mutation($data: JSON!, $surface: UUID!) {{
                create{GraphQL._upper(job)}(input: {{
                    {GraphQL._camel(job)}: {{
                        data: $data,
                        surface: $surface
                    }}
                }}) {{
                    {GraphQL._camel(job)} {{ id }}
                }}
            }}
        """, readonly=False, variable_values={
            "surface": self._surface_id(),
            "data": {
                "invocation": argv,
                "command": job.command(),
                "lot": self._lot,
                "result": self._serialize(result),
                **{key: self._serialize(value) for (key, value) in kwargs.items() if value is not None}
            }
        })

    @classmethod
    @click.command(name="graphql", cls=GroupedCommand, group="Reports", help=__doc__.split('EXAMPLES')[0])
    @click.option("--endpoint", type=str, default=DEFAULT_ENDPOINT, show_default=True, help="GraphQL HTTP endpoint to connect to")
    @click.option("--key", type=str, default=DEFAULT_API_KEY, show_default=True, help="GraphQL API key")
    @click.option("--region", type=str, default=DEFAULT_REGION, show_default=True, help="AWS region to connect to")
    @click.option("--bucket", type=str, default=DEFAULT_BUCKET, show_default=True, help="S3 bucket to write to")
    def click(endpoint, key, region, bucket):
        return {
            'bindings': GraphQL.bindings(endpoint=endpoint, key=key, region=region, bucket=bucket),
            'reporters': [ GraphQL ],
        }

    @classmethod
    def bindings(cls, endpoint, key, region, bucket):
        return [ PartialBindingSpec(GraphQL)(endpoint=endpoint, key=key, bucket=bucket, region=region) ]

    def deform(self, deformation):
        return {
            'bindings': GraphQL.bindings(endpoint=self._endpoint, key=self._key, region=self._region, bucket=self._bucket),
            'reporters': [ GraphQL ],
        }

    def command(self):
        command = ["graphql"]
        if self._endpoint != self.DEFAULT_ENDPOINT:
            command.append(f"--endpoint={self._endpoint}")
        if self._key != self.DEFAULT_API_KEY:
            command.append(f"--key={self._key}")
        return command
