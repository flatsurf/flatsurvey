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

import queue


class ConnectionPool:
    import contextlib

    def __init__(self, create, is_alive=lambda connection: True):
        self._pool = queue.Queue()
        self._create_connection = create
        self._is_alive = is_alive

    @contextlib.asynccontextmanager
    async def connect(self):
        while True:
            try:
                connection = self._pool.get(block=False)
            except queue.Empty:
                connection = await self._create_connection()
            if await self._is_alive(connection):
                break
            
            print("Discarding old connection. Retrying.")

        yield connection
        self._pool.put(connection)
