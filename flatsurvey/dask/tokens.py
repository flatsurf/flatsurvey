r"""
Tokens used to control cancelling of future and running computations.

EXAMPLES:

A :class:`SchedulerCancellationToken` is used internally by the
:class:`Scheduler`. It is used to signal whether no more new tasks should be
scheduled (see :meth:`SchedulerCancellationToken.cancel`) or running tasks
should also be stopped (see :meth:`SchedulerCancellationToken.abort`.)::

    >>> from dask.distributed import Client
    >>> from flatsurvey.dask import SchedulerCancellationToken

    >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
    >>> scheduler_token = SchedulerCancellationToken(client)

This token communicates with each :class:`WorkerCancellationToken` that has
been created from it. These tokens receive signals from the scheduler token and
can control execution on the (remote) worker::

    >>> worker_token = scheduler_token.worker_token
    >>> worker_token.is_cancelled(client)
    False

    >>> scheduler_token.cancel()
    >>> worker_token.is_cancelled(client)
    True

::

    >>> worker_token.is_aborted(client)
    False

    >>> scheduler_token.abort()
    >>> worker_token.is_aborted(client)
    True

TESTS:

Verify that this also works in an async context::

    >>> async def test():
    ...     client = await Client(processes=False, asynchronous=True, nthreads=1, preload="flatsurvey.dask.worker")
    ...     scheduler_token = SchedulerCancellationToken(client)
    ...     worker_token = scheduler_token.worker_token
    ...     print(await worker_token.is_cancelled_async(client))
    ...     scheduler_token.cancel()
    ...     await asyncio.sleep(0)
    ...     print(await worker_token.is_cancelled_async(client))
    ...     print(await worker_token.is_aborted_async(client))
    ...     scheduler_token.abort()
    ...     await asyncio.sleep(0)
    ...     print(await worker_token.is_aborted_async(client))
    ...     await client.shutdown()

    >>> import asyncio
    >>> asyncio.run(test())
    False
    True
    False
    True

"""

import threading

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
from contextlib import contextmanager

import dask.distributed

NORMAL = 0
CANCEL = 1
ABORT = 2


class SchedulerCancellationToken:
    r"""
    A token attached to a :class:`Scheduler` that can be used to signal to
    workers that they should stop operation.

    EXAMPLES::

        >>> from dask.distributed import Client
        >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
        >>> token = SchedulerCancellationToken(client)

    ::

        >>> client.shutdown()

    """

    def __init__(self, client: dask.distributed.Client):
        self._client = client
        self._state = NORMAL

        import uuid

        self._id = str(uuid.uuid4())
        self.worker_token = WorkerCancellationToken(self)

    @property
    def cancelled(self):
        r"""
        Return whether this token has been signalled to cancel, i.e., whether
        :meth:`cancel` or :meth:`abort` have been called.

        EXAMPLES::

            >>> from dask.distributed import Client
            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> token = SchedulerCancellationToken(client)

            >>> token.cancelled
            False

            >>> token.cancel()
            >>> token.cancelled
            True

        ::

            >>> token = SchedulerCancellationToken(client)

            >>> token.cancelled
            False

            >>> token.abort()
            >>> token.cancelled
            True

        """
        return self._state >= CANCEL

    def _run(self, maybe_futures):
        r"""
        Helper for :meth:`cancel` and :meth:`abort` that iterates over the
        ``maybe_futures`` and runs them asynchronously if they are futures.
        """
        if self._client.asynchronous:

            async def run_async():
                for future in maybe_futures:
                    await future

            import asyncio

            asyncio.get_running_loop().create_task(run_async())

        else:
            for _ in maybe_futures:
                pass

    def cancel(self):
        r"""
        Mark this token as cancelled.

        Notify all the corresponding worker token so that
        :meth:`WorkerCancellationToken.is_cancelled` returns ``True``.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> token = SchedulerCancellationToken(client)

            >>> token.cancel()
            >>> token.cancelled
            True

            >>> client.status
            'running'

        ::

            >>> client.shutdown()

        """
        self._state = CANCEL

        def cancel():
            yield self._client.set_metadata(self._id, self._state)
            yield self._client.run(WorkerCancellationToken.cancel, self._id)

        self._run(cancel())

    def abort(self):
        r"""
        Mark this token as aborted.

        Notify all the corresponding worker token so that
        :meth:`WorkerCancellationToken.is_cancelled` and
        :meth:`WorkerCancellationToken.is_aborted` return ``True``.

        Also runs abort callbacks in the workers and shuts down the dask
        scheduler completely.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> token = SchedulerCancellationToken(client)

            >>> token.abort()
            >>> token.cancelled
            True

            >>> client.status
            'closed'

        """
        self._state = ABORT

        def abort():
            yield self._client.set_metadata(self._id, self._state)
            yield self._client.run(WorkerCancellationToken.abort, self._id)
            yield self._client.close(1)

        self._run(abort())


class WorkerCancellationToken:
    r"""
    A serializable reference to a :class:`SchedulerCancellationToken` that can
    be sent to a dask worker.

    EXAMPLES::

        >>> from dask.distributed import Client

        >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
        >>> scheduler_token = SchedulerCancellationToken(client)

        >>> worker_token = scheduler_token.worker_token

        >>> isinstance(worker_token, WorkerCancellationToken)
        True

        >>> scheduler_token.abort()

        >>> worker_token.is_aborted(client)
        True

    """

    # A static collection of callbacks that should be executed on this worker
    # when abort() is called on the scheduler token, see on_abort() for details.
    # These callbacks are indexed by scheduler token id since a worker might be
    # attached to several schedulers over its lifetime.
    _abort_callbacks = {}

    # A static field to hold the latest reported state from the scheduler
    # token, indexed by the scheduler token id.
    # While we could also request this information from the scheduler directly,
    # it's beneficial to hold a cache of this value to reduce the network load.
    _state = {}

    # A global lock that allows us to update the above static fields in
    # non-thread-safe contexts.
    _lock = threading.Lock()

    @staticmethod
    def cancel(token: str):
        r"""
        Notify this worker that the scheduler with id ``token`` has been
        cancelled.

        This is invoked by :meth:`SchedulerCancellationToken.cancel`.

        TESTS::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> scheduler_token.cancel()

            >>> WorkerCancellationToken._state[scheduler_token._id]
            1

        ::

            >>> client.shutdown()

        """
        WorkerCancellationToken._state[token] = CANCEL

    @staticmethod
    def abort(token: str):
        r"""
        Notify this worker that the scheduler with id ``token`` has been
        aborted.

        This is invoked by :meth:`SchedulerCancellationToken.abort`.

        TESTS::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> scheduler_token.abort()

            >>> WorkerCancellationToken._state[scheduler_token._id]
            2

        """
        WorkerCancellationToken._state[token] = ABORT

        with WorkerCancellationToken._lock:
            callbacks = WorkerCancellationToken._abort_callbacks.pop(token, [])

        for callback in callbacks:
            callback()

    def __init__(self, token: SchedulerCancellationToken):
        # We only store the scheduler token id and not the entire token to keep
        # things serializable.
        self._id = token._id

    def _get_state(self) -> int:
        r"""
        Return the latest (cached) state of the scheduler token.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> worker_token = scheduler_token.worker_token

            >>> worker_token._get_state()
            0

            >>> scheduler_token.abort()
            >>> worker_token._get_state()
            2

        """
        return WorkerCancellationToken._state.get(self._id, NORMAL)

    def _refresh(self, client: dask.distributed.Client):
        r"""
        Update the cached state of the scheduler token.

        Normally, the scheduler runs our :meth:`cancel` and :meth:`abort` which
        update this value. However, this is not fully reliable if this happens
        while the worker is still booting up.
        """
        if client.asynchronous:
            raise NotImplementedError(
                "this synchronous method is not supported in an asynchronous context"
            )
        self._state[self._id] = client.get_metadata(self._id, NORMAL)

    async def _refresh_async(self, client: dask.distributed.Client):
        r"""
        Async version of :meth:`_refresh`.
        """
        if not client.asynchronous:
            raise NotImplementedError(
                "this asynchronous method is not supported in a synchronous context"
            )

        self._state[self._id] = await client.get_metadata(self._id, NORMAL)

    def is_cancelled(self, client: dask.distributed.Client) -> bool:
        r"""
        Return whether :meth:`SchedulerCancellationToken.cancel` has been called.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> worker_token = scheduler_token.worker_token

            >>> scheduler_token.abort()
            >>> worker_token.is_cancelled(client)
            True

        """
        if self._get_state() >= CANCEL:
            return True

        self._refresh(client)

        return self._get_state() >= CANCEL

    async def is_cancelled_async(self, client: dask.distributed.Client) -> bool:
        r"""
        Async version of :meth:`_is_cancelled`.
        """
        if self._get_state() >= CANCEL:
            return True

        await self._refresh_async(client)

        return self._get_state() >= CANCEL

    def is_aborted(self, client: dask.distributed.Client) -> bool:
        r"""
        Return whether :meth:`SchedulerCancellationToken.abort` has been called.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> worker_token = scheduler_token.worker_token

            >>> scheduler_token.abort()
            >>> worker_token.is_aborted(client)
            True

        """
        if self._get_state() >= ABORT:
            return True

        self._refresh(client)

        return self._get_state() >= ABORT

    async def is_aborted_async(self, client: dask.distributed.Client) -> bool:
        r"""
        Async version of :meth:`_is_aborted`.
        """
        if self._get_state() >= ABORT:
            return True

        await self._refresh_async(client)

        return self._get_state() >= ABORT

    @contextmanager
    def on_abort(self, client, callback):
        r"""
        Return a context that calls ``callback`` if
        :meth:`SchedulerCancellationToken.abort` gets called while the context
        is active.

        EXAMPLES::

            >>> from dask.distributed import Client

            >>> client = Client(processes=False, nthreads=1, preload="flatsurvey.dask.worker")
            >>> scheduler_token = SchedulerCancellationToken(client)
            >>> worker_token = scheduler_token.worker_token

            >>> with worker_token.on_abort(client, lambda: print("aborted")):
            ...     scheduler_token.abort()
            aborted

        """
        if client.asynchronous:
            raise NotImplementedError(
                "on_abort() is not implemented for asynchronous contexts yet"
            )

        with WorkerCancellationToken._lock:
            WorkerCancellationToken._abort_callbacks.setdefault(self._id, [])
            WorkerCancellationToken._abort_callbacks[self._id].append(callback)

        def cleanup():
            with WorkerCancellationToken._lock:
                if self._id in WorkerCancellationToken._abort_callbacks:
                    try:
                        WorkerCancellationToken._abort_callbacks[self._id].remove(
                            callback
                        )
                    except KeyError:
                        pass
                    if not WorkerCancellationToken._abort_callbacks[self._id]:
                        del WorkerCancellationToken._abort_callbacks[self._id]

        try:
            if self.is_aborted(dask.distributed.get_client()):
                # Note that there is a tiny race here since the callback could
                # already be running before we manage to replace it. Since the
                # callback is assumed to be thread safe and idempotent, it
                # should not matter even if it happens.
                cleanup()
                callback()
                return

            yield
        finally:
            cleanup()
