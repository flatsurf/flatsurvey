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

        self._enable_shared_bindings()

    def __repr__(self):
        return "Scheduler"

    async def start(self):
        r"""
        Run the scheduler until it has run out of jobs to schedule.

        >>> import asyncio
        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[])
        >>> asyncio.run(scheduler.start())

        """
        try:
            tasks = []

            iters = [iter(generator) for generator in self._generators]
            try:
                while iters:
                    for it in list(iters):
                        try:
                            surface = next(it)
                            command = await self._render_command(surface)
                            if command is None:
                                continue
                            tasks.append(await self._enqueue(command))
                        except StopIteration:
                            iters.remove(it)
            except KeyboardInterrupt:
                logging.info("Stopped scheduling of new jobs as requested.")

            logging.info("All jobs have been scheduled. Now waiting for jobs to finish.")

            import asyncio
            await asyncio.gather(*tasks)
        except Exception:
            if self._debug:
                import pdb
                pdb.post_mortem()
            raise

    def _enable_shared_bindings(self):
        shared = [binding for binding in self._bindings if binding.scope == "SHARED"]

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

    async def _render_command(self, surface):
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

        for goal in goals:
            await goal.consume_cache()

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

    async def _enqueue(self, command):
        r"""
        Run ``command`` once the load admits it.

        The result of this coroutine is a task that terminates when the command is completed.

        TESTS:

        We enqueue a job without worrying about the actual system load::

            >>> import asyncio
            >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[], load=0)
            >>> asyncio.run(scheduler._enqueue(["true"]))
            ...
            <Task ...>

        """
        import asyncio

        # This is a bit of a hack: Without it, the _run never actually
        # runs and we just enqueue forever (we do not need 1 for this, 0
        # works.) Without it, we schedule too many tasks but the load does not
        # go up quickly enough. See #5.
        await asyncio.sleep(1)

        if self._load > 0:
            import os
            while os.getloadavg()[0] > self._load:
                await asyncio.sleep(1)

        return asyncio.create_task(self._run(command))

    async def _run(self, command):
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

        task = local[command[0]].__getitem__(command[1:]) & BG

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
