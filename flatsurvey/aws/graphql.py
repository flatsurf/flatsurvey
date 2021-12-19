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

import os


class Client:
    def __init__(self, endpoint, key):
        from flatsurvey.aws.connection_pool import ConnectionPool

        self._readonly = ConnectionPool(
            create=lambda: _connect(endpoint, key), is_alive=_is_alive
        )
        self._readwrite = ConnectionPool(
            create=lambda: _connect_readwrite(endpoint, key), is_alive=_is_alive
        )

    async def query(self, query, description="query", **kwargs):
        r"""
        Run a query with a read-only connection.
        """
        async with self._readonly.connect() as connection:
            return await _execute(connection, query, description=description, **kwargs)

    async def mutate(self, query, description="mutation", **kwargs):
        r"""
        Run a query with a read-write connection.
        """
        async with self._readwrite.connect() as connection:
            return await _execute(connection, query, description=description, **kwargs)


def _connect_with_headers(endpoint, headers):
    from gql import Client
    from gql.transport.aiohttp import AIOHTTPTransport

    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.graphql")
    ) as source:
        schema = source.read()

    transport = AIOHTTPTransport(url=endpoint, headers=headers)
    client = Client(transport=transport, schema=schema)
    return client


async def _connect(endpoint, api_key):
    return _connect_with_headers(endpoint=endpoint, headers={"x-api-key": api_key})


async def _is_alive(connection):
    try:
        await _execute(connection, "query { __typename }", description="liveness probe")
    except Exception:
        return False
    return True


async def _connect_readwrite(endpoint, api_key):
    connection = await _connect(endpoint, api_key)
    token = (
        await _execute(
            connection,
            r"""
        mutation($mail: String!, $password: String!) {
            signin(input: {mail:$mail, password:$password}){
                jwtToken
            }
        }""",
            variable_values={
                "mail": os.environ["FLATSURVEY_GRAPHQL_LOGIN"],
                "password": os.environ["FLATSURVEY_GRAPHQL_PASSWORD"],
            },
            description="login",
        )
    )["signin"]["jwtToken"]

    return _connect_with_headers(
        endpoint=endpoint,
        headers={"x-api-key": api_key, "Authorization": f"Bearer {token}"},
    )


async def _execute(connection, query, description="query", **kwargs):
    def check(arg):
        if type(arg) == dict:
            for (key, value) in arg.items():
                check(key)
                check(value)
        elif type(arg) == list:
            for entry in arg:
                check(entry)
        elif type(arg) in [str, int, bool]:
            pass
        else:
            raise TypeError(f"Arguments must be primitive but {arg} is a {type(arg)}.")

    check(kwargs)

    if isinstance(query, str):
        from gql import gql

        try:
            query = gql(query)
        except Exception as e:
            raise Exception(f"Error in query: {query}", e)

    LIMIT = 10
    for retry in range(LIMIT):
        from concurrent.futures import TimeoutError

        from gql.transport.exceptions import (
            TransportProtocolError,
            TransportQueryError,
            TransportServerError,
        )

        if retry:
            print(f"Retrying {description} ({retry}/{LIMIT}) …")
        try:
            return await connection.execute_async(query, **kwargs)
        except TimeoutError:
            print(
                f"A {description} timed out waiting for the database server. Maybe the database is still booting?"
            )
        except TransportQueryError as e:
            print(
                f"{description} was determined to be invalid by the database server: {e}"
            )
        except TransportServerError as e:
            print(f"{description} caused an error on the database server: {e}")
        except TransportProtocolError as e:
            print(
                f"{description} caused an invalid response from the database server. Maybe the database is still booting? The response was: {e}"
            )
        except Exception as e:
            print(f"{description} failed ({type(e).__name__}): {e}")
    raise Exception(f"{description} failed after {LIMIT} retries. Giving up.")
