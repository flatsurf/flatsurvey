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

import os


class Client:
    def __init__(self, endpoint, key):
        from flatsurvey.aws.connection_pool import ConnectionPool
        self._readonly = ConnectionPool(
            create=lambda: _connect(endpoint, key),
            is_alive=_is_alive)
        self._readwrite = ConnectionPool(
            create=lambda: _connect_readwrite(endpoint, key),
            is_alive=_is_alive)

    def query(self, query, *args, description="query", **kwargs):
        r"""
        Run a query with a read-only connection.
        """
        with self._readonly.connect() as connection:
            return _execute(connection, query, *args, description=description, **kwargs)
    
    def mutate(self, query, *args, description="query", **kwargs):
        r"""
        Run a query with a read-write connection.
        """
        with self._readwrite.connect() as connection:
            return _execute(connection, query, *args, description=description, **kwargs)


def _connect_with_headers(endpoint, headers):
    from gql import Client
    from gql.transport.aiohttp import AIOHTTPTransport

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.graphql")) as source:
        schema = source.read()

    transport = AIOHTTPTransport(url=endpoint, headers=headers)
    client = Client(transport=transport, schema=schema)
    return client
    

def _connect(endpoint, api_key):
    return _connect_with_headers(endpoint=endpoint, headers={'x-api-key': api_key})


def _is_alive(connection):
    try:
        _execute(connection, "query { __typename }", description="liveness probe")
    except Exception:
        return False
    return True


def _connect_readwrite(endpoint, api_key):
    connection = _connect(api_key)
    token = _execute(client, r"""
        mutation($mail: String!, $password: String!) {
            signin(input: {mail:$mail, password:$password}){
                jwtToken
            }
        }""",
        variable_values={
            "mail": login,
            "password": password,
    }, description="login")['signin']['jwtToken']

    return _connect_with_headers(endpoint=endpoint, headers={
        'x-api-key': api_key,
        'Authorization': f"Bearer {token}"
    })
    

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


def _execute(connection, query, *args, description="query", **kwargs):
    if isinstance(query, str):
        from gql import gql
        query = gql(query)

    LIMIT = 10
    for retry in range(LIMIT):
        from concurrent.futures import TimeoutError
        from gql.transport.exceptions import TransportQueryError, TransportServerError, TransportProtocolError
        if retry:
            print(f"Retrying {description} ({retry}/{LIMIT}) …")
        try:
            return _run(connection.execute_async(query))
        except TimeoutError:
            print(f"A {description} timed out waiting for the database server. Maybe the database is still booting?")
        except TransportQueryError as e:
            print(f"{description} was determined to be invalid by the database server: {e}")
        except TransportServerError as e:
            print(f"{description} caused an error on the database server: {e}")
        except TransportProtocolError as e:
            print(f"{description} caused an invalid response from the database server. Maybe the database is still booting? The response was: {e}")
        except Exception as e:
            print(f"{description} failed: {e}")
    raise Exception(f"{description} failed after {LIMIT} retries. Giving up.")
