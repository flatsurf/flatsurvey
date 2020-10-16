import click

from pinject import copy_args_to_internal_fields

from flatsurvey.ui.group import GroupedCommand

from .report import Reporter

class DynamoDB(Reporter):
    r"""
    Report results to the DynamoDB cloud database.
    """
    @copy_args_to_internal_fields
    def __init__(self, surface, lot):
        import  boto3
        self._dynamodb = boto3.resource("dynamodb")
        self._s3 = boto3.client("s3")
        self._table = self._dynamodb.Table("flatsurvey")

    def _write(self, kind, goal, **kwargs):
        from datetime import datetime
        self._table.put_item(Item={
            "timestamp": int(datetime.now().timestamp()),
            "kind": kind,
            "goal": str(goal),
            "surface": self._serialize(self._surface),
            "lot": self._lot,
            **{key: self._serialize(value) for (key, value) in kwargs.items() if value is not None}
        })

    def _serialize(self, item):
        from pickle import dumps
        if isinstance(item, (bool, str, int)):
            return item
        return {
            "description": str(item),
            "pickle": self.s3(dumps(item)),
        };

    def s3(self, raw):
        from zlib import compress
        from uuid import uuid1
        import io
        compressed = io.BytesIO()
        compressed.write(compress(raw))
        compressed.seek(0);
        key = str(uuid1()) + ".gz"
        self._s3.put_object(ACL='public-read', Body=compressed, Key=key, Bucket='flatsurvey')
        return "https://flatsurvey.s3.eu-central-1.amazonaws.com/" + key

    def result(self, source, result, **kwargs):
        if source._required:
            self._write("result", source, result=result, **kwargs)

    def command(self):
        return ["dynamodb"]

class Cache:
    def __init__(self, surface=None):
        import  boto3
        self._dynamodb = boto3.resource("dynamodb")
        self._s3 = boto3.client("s3")
        self._table = self._dynamodb.Table("flatsurvey")

        if surface is not None:
            raise NotImplementedError

        response = self._table.scan()
        makerow = lambda row: {key: self.restore(value) for key, value in row.items() }
        self._rows = [makerow(row) for row in response['Items']]
        while response.get('LastEvaluatedKey'):
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            self._rows.extend([makerow(row) for row in response['Items']])

    def ngons(self, n):
        for row in self.results():
            if row['surface']['description'].count(',') == n - 1:
                yield row

    def polygon(self, angles):
        for row in self.results():
            if str(list(angles)) in row['surface']['description']:
                yield row

    def drop_column(self, column):
        for row in self._rows:
            self._table.update_item(Key={'timestamp': row['timestamp']}, UpdateExpression=f'REMOVE {column}')

    def restore(self, value):
        if isinstance(value, dict) and 'pickle' in value:
            # cache = None
            def load():
                # nonlocal cache
                # if cache is None:
                from zlib import decompress
                from pickle import loads
                import urllib.request
                with urllib.request.urlopen(value['pickle']) as pickle:
                    pickle = decompress(pickle.read())
                    return loads(pickle)

            value['load'] = load

        return value

    def results(self):
        rows = {}
        for row in self._rows:
            key = row['surface']['description'], row['goal']
            if key in rows:
                if rows[key]['timestamp'] > row['timestamp']: continue
            rows[key] = row

        return rows.values()


@click.command(name="dynamodb", cls=GroupedCommand, group="Reports", help=DynamoDB.__doc__)
def dynamodb():
    return DynamoDB
