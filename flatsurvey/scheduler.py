r"""
Runs a survey with dask on the local machine or in cluster.

TODO: Give full examples.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2024 Julian Rüth
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


class Scheduler:
    r"""
    A scheduler that splits a survey into commands that are sent out to workers
    via the dask protocol.

    >>> Scheduler(generators=[], bindings=[], goals=[], reporters=[])
    Scheduler

    """

    def __init__(
        self,
        generators,
        bindings,
        goals,
        reporters,
        scheduler=None,
        queue=16,
        dry_run=False,
        quiet=False,
        debug=False,
    ):
        import os

        self._generators = generators
        self._bindings = bindings
        self._goals = goals
        self._reporters = reporters
        self._scheduler = scheduler
        self._queue_limit = queue
        self._dry_run = dry_run
        self._quiet = quiet
        self._debug = debug

        # TODO: This probably does not work at all. Probably we should ditch
        # most of the progress implementation and implement something simpler
        # for the survey (and something different for the standalone worker.)
        self._report = self._enable_shared_bindings()

    def __repr__(self):
        return "Scheduler"

    async def _create_pool(self):
        r"""
        Return a new dask pool to schedule jobs.

        TODO: Explain how to use environment variables to configure things here.
        TODO: Make configurable (also without environment variables.) and comment what does not need to be configured.
        """
        import dask.config
        dask.config.set({'distributed.worker.daemon': False})

        import dask.distributed
        pool = await dask.distributed.Client(scheduler_file=self._scheduler, direct_to_workers=True, connection_limit=2**16, asynchronous=True, n_workers=8, nthreads=1, preload="flatsurvey.worker.dask")

        return pool

    async def start(self):
        r"""
        Run the scheduler until it has run out of jobs to schedule.

        >>> import asyncio
        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[])
        >>> asyncio.run(scheduler.start())

        """
        pool = await self._create_pool()

        try:
            try:
                with self._report.progress(
                    self, activity="Survey", count=0, what="tasks queued"
                ) as scheduling_progress:
                    scheduling_progress(activity="running survey")

                    with scheduling_progress(
                        "executing tasks",
                        activity="executing tasks",
                        count=0,
                        what="tasks running",
                    ) as execution_progress:
                        from more_itertools import roundrobin
                        surfaces = roundrobin(*self._generators)

                        pending = []

                        async def schedule_one():
                            return await self._schedule(pool, pending, surfaces, self._goals, scheduling_progress)

                        async def consume_one():
                            return await self._consume(pool, pending)

                        # Fill the job queue with a base line of queue_limit many jobs.
                        for i in range(self._queue_limit):
                            await schedule_one()

                        try:
                            # Wait for a result. For each result, schedule a new task.
                            while await consume_one():
                                if not await schedule_one():
                                    break
                        except KeyboardInterrupt:
                            # TODO: This does not work. The exception is not thrown here.
                            print("keyboard interrupt")
                            scheduling_progress(
                                message="stopped scheduling of new jobs as requested",
                                activity="waiting for pending tasks",
                            )
                        else:
                            scheduling_progress(
                                message="all jobs have been scheduled",
                                activity="waiting for pending tasks",
                            )

                        try:
                            # Wait for all pending tasks to finish.
                            while await consume_one():
                                pass
                        except KeyboardInterrupt:
                            execution_progress(
                                message="not awaiting scheduled jobs anymore as requested",
                                activity="waiting for pending tasks",
                            )

            except Exception:
                if self._debug:
                    import pdb

                    pdb.post_mortem()

                raise
        finally:
            await pool.close(0)

    def _enable_shared_bindings(self):
        shared = [binding for binding in self._bindings if binding.scope == "SHARED"]

        from flatsurvey.reporting.progress import Progress

        reporters = [
            reporter
            for reporter in self._reporters
            if reporter.name() == Progress.name()
        ]

        from flatsurvey.pipeline.util import ListBindingSpec

        shared.append(ListBindingSpec("reporters", reporters))

        import pinject

        import flatsurvey.reporting.report

        objects = pinject.new_object_graph(
            modules=[flatsurvey.reporting.report], binding_specs=shared
        )

        def share(binding):
            if binding.scope == "SHARED":
                from flatsurvey.pipeline.util import provide

                object = provide(binding.name, objects)

                from flatsurvey.pipeline.util import FactoryBindingSpec

                return FactoryBindingSpec(binding.name, lambda: object)

            return binding

        self._bindings = [share(binding) for binding in self._bindings]

        from flatsurvey.pipeline.util import provide

        return provide("report", objects)

    async def _schedule(self, pool, pending, surfaces, goals, scheduling_progress):
        while True:
            surface = next(surfaces, None)

            if surface is None:
                return False

            if await self._resolve_goals_from_cache(surface, self._goals):
                # Everything could be answered from cached data. Proceed to next surface.
                continue

            from flatsurvey.pipeline.util import FactoryBindingSpec, ListBindingSpec

            bindings = list(self._bindings)
            bindings.append(SurfaceBindingSpec(surface))

            from flatsurvey.worker.dask import DaskTask
            task = DaskTask(bindings=bindings, goals=self._goals, reporters=self._reporters)

            pending.append(pool.submit(task))
            return True

    async def _consume(self, pool, pending):
        import dask.distributed

        completed, still_pending = await dask.distributed.wait(pending, return_when='FIRST_COMPLETED')

        pending.clear()
        pending.extend(still_pending)

        if not completed:
            return False

        for job in completed:
            await job

        return True

    async def _resolve_goals_from_cache(self, surface, goals):
        r"""
        Return whether all ``goals`` could be resolved from cached data.
        """
        bindings = list(self._bindings)

        from flatsurvey.pipeline.util import FactoryBindingSpec, ListBindingSpec

        bindings.append(FactoryBindingSpec("surface", lambda: surface))
        bindings.append(ListBindingSpec("goals", goals))
        bindings.append(ListBindingSpec("reporters", self._reporters))

        from random import randint

        bindings.append(FactoryBindingSpec("lot", lambda: randint(0, 2**64)))

        import pinject

        import flatsurvey.cache
        import flatsurvey.jobs
        import flatsurvey.reporting
        import flatsurvey.surfaces

        objects = pinject.new_object_graph(
            modules=[
                flatsurvey.reporting,
                flatsurvey.surfaces,
                flatsurvey.jobs,
                flatsurvey.cache,
            ],
            binding_specs=bindings,
        )

        class Goals:
            def __init__(self, goals):
                self._goals = goals

        goals = [goal for goal in objects.provide(Goals)._goals]

        for goal in goals:
            await goal.consume_cache()

        goals = [goal for goal in goals if goal._resolved != goal.COMPLETED]

        return not goals


import pinject
class SurfaceBindingSpec(pinject.BindingSpec):
    def __init__(self, surface):
        self._surface = surface

    def provide_surface(self):
        return self._surface
