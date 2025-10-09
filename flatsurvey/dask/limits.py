r"""
Utilities to watch resource consumption on Linux machines.

EXAMPLES:

Limits can be used directly with the ``check`` method::

    >>> from flatsurvey.dask.limits import TimeLimit
    >>> limit = TimeLimit('1s')
    >>> limit.check()
    True

    >>> import time
    >>> time.sleep(1)
    >>> limit.check()
    False

Limits can also run in the background in async workflows::

    >>> from flatsurvey.dask.limits import TimeLimit, LimitChecker

    >>> import asyncio

    >>> async def main():
    ...     LimitChecker(TimeLimit('100ms'), lambda: print("callback executed"), period=1).start()
    ...     print("working...")
    ...     await asyncio.sleep(2)
    ...     print("done.")

    >>> asyncio.run(main())
    working...
    callback executed
    done.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2024-2025 Julian Rüth
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

import datetime
import logging

logger = logging.getLogger()


class Limit:
    r"""
    Abstract base class for a limited resource that can be checked.
    """

    def __init__(self, limit):
        self._limit = limit

    def check(self):
        r"""
        Return whether the limit has been reached.

        EXAMPLES::

            >>> from flatsurvey.dask.limits import TimeLimit
            >>> limit = TimeLimit('1ms')
            >>> limit.check()
            True

            >>> import time
            >>> time.sleep(.001)
            >>> limit.check()
            False

        """
        raise NotImplementedError("this Limit does not implement check() yet")


class LimitChecker:
    r"""
    Schedules a ``callback`` once the ``limit`` has been exceeded.

    This can only be used in an ``async`` environment.
    """

    def __init__(self, limit, callback, period=10):
        self._limit = limit
        self._callback = callback
        self._period = period

        self._task = None

    def start(self):
        r"""
        Schedule the ``limit`` to be checked every ``period`` seconds in the
        async event loop.
        """
        assert self._task is None

        import asyncio

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run())

    def stop(self):
        r"""
        Do not schedule this limit check any further.
        """
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self):
        try:
            while True:
                assert self._task is not None

                if not self._limit.check():
                    self._callback()
                    self.stop()

                import asyncio

                await asyncio.sleep(self._period)
        except Exception as e:
            import traceback

            logging.error(
                f"limit checker crashed with {''.join(traceback.format_exception(e))}"
            )


class TimeLimit(Limit):
    r"""
    A wall time limit.
    """

    def __init__(self, limit: str):
        super().__init__(TimeLimit.parse_limit(limit))

        self._start = None

    @staticmethod
    def parse_limit(limit) -> datetime.timedelta:
        r"""
        Helper method to parse ``limit`` into a Python time delta.

        EXAMPLES::

            >>> from flatsurvey.dask.limits import TimeLimit
            >>> TimeLimit.parse_limit('100ms')
            datetime.timedelta(microseconds=100000)

        """
        import pandas

        return pandas.Timedelta(limit).to_pytimedelta()  # pyright: ignore

    def check(self):
        r"""
        Return whether the wall time has advanced by the configured limit since
        this method was called for the first time.

        EXAMPLES::

            >>> from flatsurvey.dask.limits import TimeLimit
            >>> limit = TimeLimit('10ms')

            >>> import time
            >>> time.sleep(.01)

            >>> limit.check()
            True

            >>> import time
            >>> time.sleep(.01)

            >>> limit.check()
            False

        """
        import time

        now = time.time()

        if self._start is None:
            self._start = now

        verdict = now - self._start <= self._limit.total_seconds()

        if not verdict:
            logging.warning("time limit exceeded")

        return verdict


class MemoryLimit(Limit):
    r"""
    A limit on the total RAM and swap memory used by this process.

    EXAMPLES::

        >>> from flatsurvey.dask.limits import MemoryLimit
        >>> limit = MemoryLimit(2**30)
        >>> limit.check()
        True

    Each int uses four bytes, so we exceed the memory limit by allocating that
    many ints::

        >>> A = [0] * 2**28
        >>> limit.check()
        False

    """

    def __init__(self, limit: str):
        super().__init__(limit)

        # Verify that the limit is valid
        MemoryLimit.parse_limit(limit)

    @staticmethod
    def parse_limit(limit) -> int:
        import psutil

        ram = psutil.virtual_memory().total
        cpus = psutil.cpu_count()

        if cpus is None:
            import warnings

            warnings.warn(
                "System failed to report the number of available CPU threads. Assuming single CPU thread."
            )
            cpus = 1

        if limit == "conservative":
            return int(ram / cpus / 2)

        if limit == "standard":
            return int(ram / cpus)

        if limit == "overcommit":
            return int(ram / cpus * 1.5)

        from datasize import DataSize

        return int(DataSize(limit))

    @staticmethod
    def memory(pid: int | None = None):
        r"""
        Return the total memory (Rss + Swap) used by the process with ``pid``.

        If no ``pid`` is given, then return the total memory used by this
        process and its child processes.
        """
        import os

        if pid is None:
            pid = os.getpid()

            import psutil

            parent = psutil.Process(pid)

            from collections import defaultdict

            memory = defaultdict(lambda: 0)

            children = [child.pid for child in parent.children(recursive=True)]
            children.append(pid)

            for child in children:
                for kind, value in MemoryLimit.memory(child).items():
                    memory[kind] += value

            return memory

        smap = f"/proc/{pid}/smaps"

        entries = {}

        with open(smap, "r") as smap:
            for line in smap:
                items = line.split()

                if not items[0].endswith(":"):
                    continue
                if len(items) != 3:
                    continue
                if items[2] != "kB":
                    continue

                key = items[0][:-1]
                value = int(items[1]) * 1024
                entries[key] = entries.get(key, 0) + value

        return entries

    def check(self):
        smap = MemoryLimit.memory()
        verdict = smap["Rss"] + smap["Swap"] <= MemoryLimit.parse_limit(self._limit)

        if not verdict:
            logging.warning("memory limit exceeded")

        return verdict
