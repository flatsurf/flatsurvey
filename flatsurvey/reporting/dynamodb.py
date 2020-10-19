r"""
Reports survey results to Amazon's DynamoDB.

Note that you need AWS credentials configured to perform writing operations,
typically by creating ``~/.aws/credentials``.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "dynamodb", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker dynamodb [OPTIONS]
      Reports results to Amazon's DynamoDB cloud database.
    Options:
      --region TEXT  AWS region to connect to  [default: eu-central-1]
      --table TEXT   DynamoDB table to write to  [default: flatsurvey]
      --bucket TEXT  S3 bucket to write to  [default: flatsurvey]
      --help         Show this message and exit.

Note that throughout the doctests here, we mock DynamoDB and S3 with moto so
we do not actually write to the real AWS.

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

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.pipeline.util import PartialBindingSpec

class DynamoDB(Reporter):
    r"""
    Reports results to Amazon's DynamoDB cloud database.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> from moto import mock_dynamodb2, mock_s3
        >>> with mock_dynamodb2(), mock_s3():
        ...     DynamoDB(surface=surface, lot=1337)
        dynamodb

    """
    DEFAULT_REGION = "eu-central-1"
    DEFAULT_TABLE = "flatsurvey"
    DEFAULT_BUCKET = "flatsurvey"

    @copy_args_to_internal_fields
    def __init__(self, surface, lot, table=DEFAULT_TABLE, bucket=DEFAULT_BUCKET, region=DEFAULT_REGION):
        import boto3
        self._dynamodb = boto3.client("dynamodb", region_name=region)

        existing_tables = self._dynamodb.list_tables()['TableNames']
        if table not in existing_tables:
            self._dynamodb.create_table(TableName=table,
                AttributeDefinitions=[{
                    "AttributeName": "uuid",
                    "AttributeType": "S",
                }, {
                    "AttributeName": "surface-key",
                    "AttributeType": "S",
                }, {
                    "AttributeName": "job",
                    "AttributeType": "S",
                }],
                KeySchema=[{
                    "AttributeName": "uuid",
                    "KeyType": "HASH",
                }],
                GlobalSecondaryIndexes=[{
                    "IndexName": "surface-job",
                    "KeySchema": [{
                        "AttributeName": "surface-key",
                        "KeyType": "HASH",
                    }, {
                        "AttributeName": "job",
                        "KeyType": "RANGE",
                    }],
                    "Projection": {
                        "ProjectionType": "KEYS_ONLY",
                    },
                }],
                BillingMode="PAY_PER_REQUEST")

            self._dynamodb.get_waiter('table_exists').wait(TableName=table)

        self._s3 = boto3.client("s3", region_name=region)
        if not any(b['Name'] == bucket for b in self._s3.list_buckets()['Buckets']):
            self._s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": region})

    @classmethod
    def table(self, table=DEFAULT_TABLE, region=DEFAULT_REGION):
        r"""
        Connect to DynamoDB and return a proxy for ``table``.

        EXAMPLES::

            >>> DynamoDB.table()
            dynamodb.Table(name='flatsurvey')

        """
        import boto3
        return boto3.resource("dynamodb", region_name=region).Table(table)

    def _write(self, job, **kwargs):
        r"""
        Write data to the database table to register a result for the job ``job``.

        EXAMPLES::

            >>> from flatsurvey.reporting.report import Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.cache import Cache

            >>> surface = Ngon((1, 1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=Report([]), flow_decompositions=flow_decompositions)

        We use a mock for DynamoDB in this example so we do not actually talk to AWS::

            >>> from moto import mock_dynamodb2, mock_s3
            >>> with mock_dynamodb2(), mock_s3():
            ...     log = DynamoDB(surface=surface, lot=1337)
            ...     # We log that a run to resolve ccp has been inconclusive and get that result back from the cache.
            ...     log._write(job=ccp, result=None)
            ...     assert Cache().result(surface=surface, job=ccp).reduce() == None, "expected unconclusive result"
            ...     # We now log that we found this surface not to be completely
            ...     # cylinder periodic and get that result back from the cache as the
            ...     # combination of both stored results.
            ...     log._write(job=ccp, result=False)
            ...     assert Cache().result(surface=surface, job=ccp).reduce() == False, "expected negative result"
            ...     # Note that even when we ask for this result for another
            ...     # quadrilateral with the same angles, we get the same verdict since
            ...     # it does not depend on the exact (random) choice of side lengths.
            ...     assert Cache().result(surface=Ngon((1, 1, 1, 1)), job=ccp).reduce() == False, "expected another negative result"
            ...     # Unless we force the cache only to consider rows that
            ...     # exactly match this surface.
            ...     assert Cache().result(surface=surface, job=ccp, exact=True).reduce() == False, "expected yet another negative result"
            ...     assert Cache().result(surface=Ngon((1, 1, 1, 1)), job=ccp, exact=True).reduce() == None, "expected unconclusive result again"
            
        """
        from datetime import datetime
        timestamp = int(datetime.now().timestamp())

        import sys
        argv = sys.argv
        if argv and argv[0] == "-m": argv = argv[1:]

        from uuid import uuid4
        DynamoDB.table(table=self._table, region=self._region).put_item(Item={
            "uuid": str(uuid4()),
            "surface-key": str(self._surface),
            "job": type(job).__name__,
            "timestamp": timestamp,
            "invocation": argv,
            "command": job.command(),
            "surface": self._serialize(self._surface),
            "lot": self._lot,
            **{key: self._serialize(value) for (key, value) in kwargs.items() if value is not None}
        })

    def s3(self, raw):
        r"""
        Write the ``raw`` pickle string to an S3 bucket and return its URL.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        We use a mock for DynamoDB in this example so we do not actually talk to AWS::

            >>> from pickle import dumps
            >>> from moto import mock_dynamodb2, mock_s3
            >>> with mock_dynamodb2(), mock_s3():
            ...     log = DynamoDB(surface=surface, lot=1337)
            ...     url = log.s3(dumps(surface))
            ...     # When we write the surface again to S3, nothing is actually stored:
            ...     assert log.s3(dumps(surface)) == url
            
            >>> url
            's3://flatsurvey/748a9f2ed2b6be948db5ed59cf84eb7090872d92b7bd69d45f47c93a16aca790.pickle.gz'

        """
        from zlib import compress
        import io
        import hashlib

        sha = hashlib.sha256()
        sha.update(raw)
        key = f"pickles/{sha.hexdigest()}.pickle.gz"

        compressed = io.BytesIO()
        compressed.write(compress(raw))
        compressed.seek(0);

        self._s3.put_object(ACL='public-read', Body=compressed, Key=key, Bucket=self._bucket)
        return f"s3://{self._bucket}/{key}"

    def _serialize(self, item):
        r"""
        Return a serialized version of ``item`` that can be stored in DynamoDB.

        Note that types can augment this by implementing a method `_flatsurvey_characteristics`.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        We use a mock for DynamoDB in this example so we do not actually talk to AWS::

            >>> from moto import mock_dynamodb2, mock_s3
            >>> with mock_dynamodb2(), mock_s3():
            ...     log = DynamoDB(surface=surface, lot=1337)
            ...     assert log._serialize(1) == 1
            ...     assert log._serialize(False) == False
            ...     assert log._serialize("abc") == "abc"
            ...     assert log._serialize([1, 2]) == [1, 2]
            ...     assert log._serialize(surface) == {
            ...         "angles": [1, 1, 1],
            ...         "description": "Ngon((1, 1, 1))",
            ...         "pickle": "s3://flatsurvey/748a9f2ed2b6be948db5ed59cf84eb7090872d92b7bd69d45f47c93a16aca790.pickle.gz"
            ...     }

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
            dump = ("Failed: " + str(e)).encode('UTF-8')
        return {
            **characteristics,
            "description": str(item),
            "pickle": self.s3(dump),
        };

    def result(self, job, result, **kwargs):
        r"""
        Write the ``result`` of ``job`` to DynamoDB.

        EXAMPLES::

            >>> from flatsurvey.reporting.report import Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.cache import Cache

            >>> surface = Ngon((1, 1, 1, 1))
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
            >>> ccp = CompletelyCylinderPeriodic(report=Report([]), flow_decompositions=flow_decompositions)

        We use a mock for DynamoDB in this example so we do not actually talk to AWS::

            >>> from moto import mock_dynamodb2, mock_s3
            >>> with mock_dynamodb2(), mock_s3():
            ...     log = DynamoDB(surface=surface, lot=1337)
            ...     # We log that a run to resolve ccp has been inconclusive and get that result back from the cache.
            ...     log.result(job=ccp, result=None)
            ...     assert Cache().result(surface=surface, job=ccp).reduce() == None, "expected unconclusive result"

        """
        self._write(job, result=result, **kwargs)

    @classmethod
    @click.command(name="dynamodb", cls=GroupedCommand, group="Reports", help=__doc__.split('EXAMPLES')[0])
    @click.option("--region", type=str, default=DEFAULT_REGION, show_default=True, help="AWS region to connect to")
    @click.option("--table", type=str, default=DEFAULT_TABLE, show_default=True, help="DynamoDB table to write to")
    @click.option("--bucket", type=str, default=DEFAULT_BUCKET, show_default=True, help="S3 bucket to write to")
    def click(region, table, bucket):
        return {
            'bindings': [ PartialBindingSpec(DynamoDB)(region=region, table=table, bucket=bucket) ],
            'reporters': [ DynamoDB ],
        }

    def command(self):
        command = ["dynamodb"]
        if self._region != self.DEFAULT_REGION:
            command.append(f"--region={self._region}")
        if self._table != self.DEFAULT_TABLE:
            command.append(f"--table={self._table}")
        if self._bucket != self.DEFAULT_BUCKET:
            command.append(f"--bucket={self._bucket}")
        return command
