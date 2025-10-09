r"""
Runs a survey with dask on the local machine or in a cluster.

This implements a (somewhat unnecessary) wrapper for the dask API.

EXAMPLES:

We compute the orbit closure of the (1,1,1) and the (1,1,2) triangles::

    >>> from flatsurvey.pipeline import Bindings, Goal
    >>> survey = Bindings()

    >>> from flatsurvey.surfaces import Surface, Ngons
    >>> ngons = Ngons(vertices=3, min=0, limit=None, count=2, literature='include', family=None, filter=None)
    >>> survey.survey(Surface, ngons)

    >>> from flatsurvey.jobs import OrbitClosure
    >>> survey.append(list[Goal], OrbitClosure)

    >>> scheduler = Scheduler(survey_bindings=survey.survey_bindings)

    >>> import asyncio
    >>> asyncio.run(scheduler.start())

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
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

import logging
from contextlib import contextmanager
from typing import Iterator, List

import dask.distributed

from flatsurvey.dask.limits import MemoryLimit, TimeLimit
from flatsurvey.dask.tokens import SchedulerCancellationToken
from flatsurvey.pipeline import Bindings
from flatsurvey.ui import Progress

logger = logging.getLogger()


class Scheduler:
    r"""
    A scheduler that splits a survey into tasks that are sent out to workers
    via the dask protocol.

    INPUT::

    - ``survey_bindings`` -- an iterator of :class:`Bindings` that lists which
      computations should be performed by this survey, usually created with
      :meth:`Bindings.survey_bindings`.

    - ``scheduler`` -- a dask scheduler file to connect to; if not given (the
      default) then a dedicated dask scheduler is launched

    - ``queue_limit`` -- the number of processes to initially submit into the
      dask scheduler before we wait for workers to finish (default: thrice the
      number of worker threads provided by the dask scheduler)

    ALGORITHM:

    We'll have lots of jobs, (e.g., surfaces,) that we want to run with one
    scheduler usually. Often even an infinite family. So we cannot submit all
    the jobs into the dask job queue and wait for them to complete.

    Instead, we try to keep a good amount of a "backlog" in the queue so that
    our workers never run out of things to do. Whenever a worker finishes a
    job, we try to keep the queue equally full by finding a new job to submit
    into the queue (this might take a while since we might be able to obtain
    the results for a lot of configurations from our caches and won't submit
    them into the queue therefore.)

    EXAMPLES::

        >>> Scheduler(survey_bindings=[])
        Scheduler(…)

    """

    def __init__(
        self,
        survey_bindings: Iterator[Bindings],
        mem_limit: MemoryLimit | None = None,
        time_limit: TimeLimit | None = None,
        progress: Progress | None = None,
        scheduler_json=None,
        queue_limit=None,
    ):

        if progress is None:
            from flatsurvey.ui.progress import SilentProgress

            progress = SilentProgress()

        self._survey_bindings = iter(survey_bindings)
        self._memory_limit = mem_limit
        self._time_limit = time_limit
        self._progress: Progress = progress
        self._scheduler_json = scheduler_json
        self._queue_limit = queue_limit

    def __repr__(self):
        return "Scheduler(…)"

    async def start(self):
        r"""
        Run the scheduler until all jobs have been scheduled and all jobs
        terminated.

        EXAMPLES::

            >>> import asyncio
            >>> scheduler = Scheduler(survey_bindings=[])
            >>> asyncio.run(scheduler.start())  # random progress output

        """
        pool = await self._create_pool()

        with self._create_sigint_handler(pool) as token:
            try:
                jobs = await self._seed_jobs(pool, self._progress, token)

                if not jobs:
                    logging.info("no jobs were required to complete this survey")
                    return

                await self._submit_jobs(pool, self._progress, token, jobs)
                await self._await_pending_jobs(self._progress, jobs)
            finally:
                # Terminate all workers immediately if we crash out of this code
                # block. (If we terminated normally, then there's nothing we have
                # to wait for.
                await pool.close(0)  # pyright: ignore[reportGeneralTypeIssues]
                if self._scheduler_json is None:
                    # Shut down the scheduler & workers that we started.
                    await pool.shutdown()

    @contextmanager
    def _create_sigint_handler(self, pool: dask.distributed.Client):
        r"""
        Replace the handler for the SIGINT signal while this context is active
        so that pressing Ctrl-C aborts the survey.

        .. NOTE:

            The signal handling that SageMath (or rather cysignals) installs
            for the SIGINT (i.e., Ctrl-C) signal does not play well in the
            (async?) dask world. What exactly happens is unclear but somehow
            when our ``_consume()`` entered ``dask.distributed.wait()`` and
            then we press Ctrl-C, a SIGABRT is raised (or at least it says
            "Aborted!" in the terminal) and then this asynchronous execution
            thread basically disappears. The program eventually exits but no
            exception is raised, and no finally blocks are executed here.

            Whatever is going on exactly, we don't want any special handling of
            Ctrl-C in the scheduling process. When Ctrl-C is pressed while
            SageMath is doing something (say doing a bit of arithmetic to
            figure out what's the next surface to survey) that's usually very
            fast and we cannot interrupt it safely anyway. So we do not rely on
            the KeyboardInterrupt at all here but just handle SIGINT ourselves
            to cancel/abort the survey.

        EXAMPLES::

            >>> scheduler = Scheduler(survey_bindings=[])

            >>> import os, signal

            >>> async def test():
            ...     pool = await scheduler._create_pool()
            ...     with scheduler._create_sigint_handler(pool) as token:
            ...         print(token.cancelled)
            ...         os.kill(os.getpid(), signal.SIGINT)
            ...         print(token.cancelled)
            ...         os.kill(os.getpid(), signal.SIGINT)
            ...         print(token.cancelled)
            ...     await pool.close()

            >>> import asyncio
            >>> asyncio.run(test())
            False
            True
            True

        """
        token = SchedulerCancellationToken(pool)

        def handle_sigint(_, __):
            if token.cancelled:
                token.abort()
            else:
                token.cancel()

        import signal

        from cysignals.pysignals import changesignal

        with changesignal(signal.SIGINT, handle_sigint):
            yield token

    async def _create_pool(self) -> dask.distributed.Client:
        r"""
        Return a dask pool to schedule jobs.

        This is a helper method for :meth:`start`.

        EXAMPLES::

            >>> scheduler = Scheduler(survey_bindings=[])

            >>> async def create_pool():
            ...     pool = await scheduler._create_pool()
            ...     await pool.close(0)

            >>> import asyncio
            >>> asyncio.run(create_pool())

        """
        import dask.config

        # We do not spawn workers as daemons so that they can have child
        # processes, see worker/dask.py (only has an effect if no
        # scheduler_file is set.)
        dask.config.set({"distributed.worker.daemon": False})

        from multiprocessing import cpu_count

        import dask.distributed

        return await dask.distributed.Client(
            scheduler_file=self._scheduler_json,
            direct_to_workers=True,
            # Connections are not very expensive but this number should be big
            # enough so that we can communicate with all workers in large
            # clusters.
            connection_limit=2**16,
            # We want to use dask through its modern asynchronous API.
            asynchronous=True,
            # The following parameters are only relevant when not providing our
            # own scheduler.
            # Start a worker for each execution thread on the CPU.
            n_workers=cpu_count(),
            # We run each worker single-threaded, see worker/dask.py.
            threads_per_worker=1,
            # We preload worker/dask.py unless scheduler_file is set, see
            # documentation there.
            preload="flatsurvey.dask.worker",
            # We would like to spawn isolated processes but this parameter
            # seems to be ignored as of mid 2025. We do get n_workers workers
            # but they all live in the same process actually.
            processes=True,
            # Disable the dask nanny, see module documentation of worker/dask.py
            worker_class=dask.distributed.Worker,
        )

    async def _seed_jobs(
        self,
        pool: dask.distributed.Client,
        progress: Progress,
        token: SchedulerCancellationToken,
    ) -> List[dask.distributed.Future]:
        r"""
        Initialize the job queue with some things to work on without actually
        consuming results from the workers that might arrive in the meantime.

        This is a helper method for :meth:`start`.

        """
        progress.set_activity("seeding job queue")

        jobs = []

        # Fill the job queue with a base line of queue_limit many jobs.
        for _ in range(self._queue_limit or 3 * sum((await pool.nthreads()).values())):
            job = await self._submit_job(pool, progress, token)
            if job is None:
                break
            jobs.append(job)

        return jobs

    async def _submit_job(
        self,
        pool: dask.distributed.Client,
        progress: Progress,
        token: SchedulerCancellationToken,
    ) -> dask.distributed.Future | None:
        r"""
        Enqueue another task for computation on a worker.

        Return a future that resolves when the job completes or ``None`` if all
        tasks have been scheduled already.

        This will skip over tasks that can be resolved from cached data.

        This is a helper method for :meth:`_seed_jobs` and :meth:`submit_jobs`.

        """
        while True:
            if token.cancelled:
                return None

            bindings = next(self._survey_bindings, None)

            if bindings is None:
                return None

            if token.cancelled:
                return None

            cached = await self._resolve_from_cache(bindings)

            if cached:
                # Everything could be answered from cached data. Proceed to next task.
                continue

            # Forget about the precise values that were created to answer from
            # the cache.
            bindings = bindings.clone(repr(bindings))

            # Make sure that the workers do not access the cache (it won't
            # speed things up there.)
            from flatsurvey.cache import Cache

            bindings.forget(Cache)

            limits = []
            if self._time_limit is not None:
                limits.append(self._time_limit)
            if self._memory_limit is not None:
                limits.append(self._memory_limit)

            from flatsurvey.dask.task import Task

            task = Task(bindings, limits=limits)

            if token.cancelled:
                return None

            progress.queued()

            return pool.submit(task, token.worker_token)

    @staticmethod
    async def _resolve_from_cache(bindings: Bindings):
        r"""
        Return whether all ``goals`` for the task encoded in the ``bindings``
        could be resolved from cached data.

        This is a helper method for :meth:`_submit_job`.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings, Goal
            >>> bindings = Bindings()
            >>> bindings.define(Goal, [])

            >>> import asyncio
            >>> asyncio.run(Scheduler._resolve_from_cache(bindings))
            True

        ::

            >>> from flatsurvey.jobs import OrbitClosure
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> bindings = Bindings()
            >>> bindings.append(list[Goal], OrbitClosure)
            >>> bindings.define(Surface, Ngon((1, 1, 1)))

            >>> import asyncio
            >>> asyncio.run(Scheduler._resolve_from_cache(bindings))
            False

        """
        from flatsurvey.pipeline import Goal

        goals = bindings.get(list[Goal], [])

        for goal in goals:
            await goal.consume_cache()

        pending_goals = [goal for goal in goals if not goal.resolved]

        return not pending_goals

    async def _submit_jobs(
        self,
        pool: dask.distributed.Client,
        progress: Progress,
        token: SchedulerCancellationToken,
        jobs: List[dask.distributed.Future],
    ) -> None:
        r"""
        Submit jobs for all ``surfaces`` to run in the ``pool`` of workers.

        This is a helper method for :meth:`start`.
        """
        progress.set_activity("scheduling jobs as needed")

        # Wait for a result. For each result, schedule a new task.
        while True:
            if token.cancelled:
                logging.info("stopped scheduling of new jobs as requested")
                return

            assert (
                jobs
            ), "_submit_jobs needs jobs to wait for to keep the job queue filled"

            completed = await self._await_pending_job(progress, jobs)
            assert completed, "await_pending_job must only return when a job terminated"

            for _ in range(completed):
                job = await self._submit_job(pool, progress, token)
                if job is None:
                    if token.cancelled:
                        logging.info("stopped scheduling of new jobs as requested")
                        return

                    logging.info("all jobs have been scheduled")
                    return

                jobs.append(job)

    async def _await_pending_jobs(
        self, progress: Progress, jobs: List[dask.distributed.Future]
    ):
        r"""
        Wait for all ``jobs`` to complete.

        This is a helper method for :meth:`start`.
        """
        progress.set_activity("waiting for jobs to finish")
        while await self._await_pending_job(progress, jobs):
            pass

    async def _await_pending_job(
        self, progress: Progress, jobs: List[dask.distributed.Future]
    ) -> int:
        r"""
        Wait for at least one of the ``jobs`` to complete and remove completed
        job from that list.

        Return the number of jobs that completed.

        This is a helper method for :meth:`_await_pending_jobs` and
        :meth:`_submit_jobs`.
        """
        if not jobs:
            return 0

        completed, still_pending = await dask.distributed.wait(
            jobs, return_when="FIRST_COMPLETED"
        )

        jobs.clear()
        jobs.extend(still_pending)

        assert completed, "wait() only returns when a job terminates"

        for job in completed:
            progress.completed()
            try:
                result = await job
                assert not isinstance(result, Exception)
            except Exception as e:
                logging.error(f"Task crashed with {e}. Skipping.")

        return len(completed)
