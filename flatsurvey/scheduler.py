# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2022 Julian Rüth
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
    A simple scheduler that splits a survey into commands that are run on the local
    machine when the load admits it.

    >>> Scheduler(generators=[], bindings=[], goals=[], reporters=[])
    Scheduler

    """

    def __init__(
        self,
        generators,
        bindings,
        goals,
        reporters,
        dry_run=False,
        load=None,
        quiet=False,
        debug=False,
    ):
        import os

        if load is None:
            load = os.cpu_count()

        self._generators = generators
        self._bindings = bindings
        self._goals = goals
        self._reporters = reporters
        self._dry_run = dry_run
        self._load = load
        self._quiet = quiet
        self._jobs = []
        self._debug = debug

        self._report = self._enable_shared_bindings()

    def __repr__(self):
        return "Scheduler"

    async def start(self):
        r"""
        Run the scheduler until it has run out of jobs to schedule.

        >>> import asyncio
        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[])
        >>> asyncio.run(scheduler.start())

        """
        MAX_QUEUE = 32

        try:
            with self._report.progress(self, activity="Survey", count=0, what="tasks queued") as scheduling_progress:
                scheduling_progress(activity="running survey")

                with scheduling_progress("executing tasks", activity="executing tasks", count=0, what="tasks running") as execution_progress:
                    submitted_tasks = []

                    from collections import deque
                    queued_commands = deque()

                    surfaces = [iter(generator) for generator in self._generators]

                    try:
                        while True:
                            import asyncio
                            await asyncio.sleep(0)

                            message = []

                            try:
                                if queued_commands:
                                    # Attempt to run a task (unless the load is too high)
                                    import os
                                    load = os.getloadavg()[0]

                                    import psutil
                                    psutil.cpu_percent(None)
                                    cpu = psutil.cpu_percent(0.01)

                                    if self._load > 0 and load > self._load:
                                        message.append(f"load {load:.1f} too high")
                                    elif self._load > 0 and cpu >= 100:
                                        message.append(f"CPU {cpu:.1f}% too high")
                                    else:
                                        import asyncio
                                        submitted_tasks.append(asyncio.create_task(self._run(queued_commands.popleft(), execution_progress)))

                                        continue

                                if len(queued_commands) >= MAX_QUEUE or (not surfaces and queued_commands):
                                    message.append("queue full")
                                    import asyncio
                                    await asyncio.sleep(1)
                                    continue
                            finally:
                                scheduling_progress(count=len(queued_commands), message=" and ".join(message))

                            if not surfaces and not queued_commands:
                                break

                            with scheduling_progress(source="rendering task", activity="rendering task") as rendering_progress:
                                generator = surfaces[0]
                                surfaces = surfaces[1:] + surfaces[:1]

                                try:
                                    surface = next(generator)
                                except StopIteration:
                                    surfaces.pop()
                                    continue

                                rendering_progress(message="determining goals", activity=f"rendering task for {surface}")

                                command = await self._render_command(surface, scheduling_progress)

                                if command is None:
                                    continue

                                queued_commands.append(command)
                                scheduling_progress(count=len(queued_commands))

                    except KeyboardInterrupt:
                        scheduling_progress(message="stopped scheduling of new jobs as requested", activity="waiting for pending tasks")
                    else:
                        scheduling_progress(message="all jobs have been scheduled", activity="waiting for pending tasks")

                    import asyncio
                    await asyncio.gather(*submitted_tasks)

        except Exception:
            if self._debug:
                import pdb
                pdb.post_mortem()

            raise

    def _enable_shared_bindings(self):
        shared = [binding for binding in self._bindings if binding.scope == "SHARED"]

        from flatsurvey.reporting.progress import Progress
        reporters = [reporter for reporter in self._reporters if reporter.name() == Progress.name()]

        from flatsurvey.pipeline.util import ListBindingSpec
        shared.append(ListBindingSpec("reporters", reporters))

        import pinject
        objects = pinject.new_object_graph(modules=[], binding_specs=shared)

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

    async def _render_command(self, surface, progress):
        r"""
        Return the command to invoke a worker to compute the ``goals`` for ``surface``.

        >>> import asyncio
        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import OrbitClosure

        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[OrbitClosure], reporters=[])
        >>> command = scheduler._render_command(Ngon([1, 1, 1]))
        >>> asyncio.run(command)  # doctest: +ELLIPSIS
        ['python', '-m', 'flatsurvey.worker', 'orbit-closure', 'pickle', '--base64', '...']

        """
        bindings = list(self._bindings)

        from flatsurvey.pipeline.util import FactoryBindingSpec, ListBindingSpec

        bindings.append(FactoryBindingSpec("surface", lambda: surface))
        bindings.append(ListBindingSpec("goals", self._goals))
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

        commands = []

        class Reporters:
            def __init__(self, reporters):
                self._reporters = reporters

        reporters = objects.provide(Reporters)._reporters
        for reporter in reporters:
            commands.extend(reporter.command())

        class Goals:
            def __init__(self, goals):
                self._goals = goals

        goals = [
            goal
            for goal in objects.provide(Goals)._goals
        ]

        with progress("resolving goals from cached data", activity="resolvivg goals from cached data", total=len(goals), count=0, what="goals") as resolving_progress:
            for goal in goals:
                await goal.consume_cache()
                resolving_progress(advance=1)

        goals = [goal for goal in goals if goal._resolved != goal.COMPLETED]

        if not goals:
            return None

        for goal in goals:
            commands.extend(goal.command())

        for binding in self._bindings:
            from flatsurvey.pipeline.util import provide
            binding = provide(binding.name, objects)
            if binding in reporters:
                continue
            if binding in goals:
                continue
            if binding == surface:
                continue

            # We already consumed the cache above. There is no need to have the
            # worker reread the cache.
            from flatsurvey.cache import Cache
            if binding.name() == Cache.name():
                continue

            commands.extend(binding.command())

        commands.extend(surface.command())

        import os

        return [
            os.environ.get("PYTHON", "python"),
            "-m",
            "flatsurvey.worker",
        ] + commands

    async def _run(self, command, progress):
        r"""
        Run ``command``.

        # Currently, pytest fails to test these with a "fileno" error, see #4.
        # >>> scheduler = Scheduler(generators=[], goals=[], reporters=[], bindings=[], load=None)
        # >>> asyncio.run(scheduler._run(["echo", "hello world"]))
        # hello world
        # >>> asyncio.run(scheduler._run(["no-such-command"]))
        # Traceback (most recent call last):
        # ...
        # plumbum.commands.processes.CommandNotFound: ...
        # >>> asyncio.run(scheduler._run(["false"]))
        # Traceback (most recent call last):
        # ...
        # plumbum.commands.processes.ProcessExecutionError: Unexpected exit code: ...

        """
        if self._dry_run:
            if not self._quiet:
                logging.info(" ".join(command))
            return

        from plumbum import BG, local
        from plumbum.commands.processes import ProcessExecutionError

        with self._report.progress(source=command) as worker_progress:
            task = local[command[0]].__getitem__(command[1:]) & BG
            progress(advance=1)
            try:
                try:
                    while not task.ready():
                        import asyncio
                        await asyncio.sleep(1)

                    if task.stdout:
                        # We should have better monitoring, see #41.
                        logging.warning("Task produced output on stdout:\n" + task.stdout)
                except ProcessExecutionError as e:
                    # We should have better monitoring, see #41.
                    logging.error("Process crashed: " + " ".join(command) + "\n" + str(e))
            finally:
                progress(advance=-1)
