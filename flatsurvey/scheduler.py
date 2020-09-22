r"""
Schedules jobs on the local machine as the load permits it.
"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import asyncio

from .pipeline import graph, provide
from .reports import Log

class Scheduler:
    r"""
    A simple scheduler that splits a survey into commands that are run on the local
    machine when the load admits it.

    >>> Scheduler(objects=[], goals=[])
    Scheduler()

    """
    def __init__(self, objects, goals, reporters, dry_run=False, load=1., quiet=False):
        self._objects = objects
        self._goals = goals
        self._reporters = reporters
        self._dry_run = dry_run
        self._load = load
        self._quiet = quiet
        self._jobs = []

    def __repr__(self): return "Scheduler"

    async def start(self):
        r"""
        Run the scheduler until it has run out of jobs to schedule.

        >>> scheduler = Scheduler(objects=[], goals=[])
        >>> asyncio.run(scheduler.start())

        """
        tasks = []
        nothing = object()
        from itertools import zip_longest, chain
        iters = [iter(objects) for objects in self._objects]
        while iters:
            for it in list(iters):
                try:
                    surface = next(it)
                    tasks.append(await self._schedule(surface, self._goals, self._reporters))
                except StopIteration:
                    iters.remove(it)

        print("All jobs have been scheduled. Now waiting for jobs to finish.")
        await asyncio.gather(*tasks)

    async def _schedule(self, source, goals, reporters):
        r"""
        Schedule a single job, i.e., have all ``goals`` computed for a ``source``.

        >>> from survey.objects.ngons import Ngon
        >>> from survey.goals.orbit_closure import OrbitClosure

        >>> scheduler = Scheduler(objects=[], goals=[], dry_run=True)
        >>> task = asyncio.run(scheduler._schedule(Ngon([1, 1, 1]), [OrbitClosure]))
        python -m survey.worker pickle --base64 eJxrYEouLi0qS63UK84vLUpOLdbLS8/PK+byA5JchQyajYWMtYVMGhFsDAwMiXnpOanFhcyxhSwa3owgmAoWz0nNSy/JKGSN4AJyUisSk0t0i1ITcwrZSpP0AKaNHA0= orbit-closure
        >>> task.result()

        """
        command = self._render_command(source, goals, reporters)
        return await self._enqueue(command)

    def _render_command(self, source, goals, reporters):
        r"""
        Return the command to invoke a worker to compute the ``goals`` for ``source``.

        >>> from survey.objects.ngons import Ngon
        >>> from survey.goals.orbit_closure import OrbitClosure

        >>> scheduler = Scheduler(objects=[], goals=[])
        >>> scheduler._render_command(Ngon([1, 1, 1]), [OrbitClosure])
        ['python', '-m', 'survey.worker', 'pickle', '--base64', 'eJxrYEouLi0qS63UK84vLUpOLdbLS8/PK+byA5JchQyajYWMtYVMGhFsDAwMiXnpOanFhcyxhSwa3owgmAoWz0nNSy/JKGSN4AJyUisSk0t0i1ITcwrZSpP0AKaNHA0=', 'orbit-closure']

        """
        import os
        from itertools import chain
        from .objects.surface import Surface

        # TODO: This code is duplicated between the two __main__s
        objects = graph(
            provide('surface', lambda: source),
            provide('reporters', lambda: reporters),
            provide('goals', lambda: goals),
        )

        reporters = [objects.provide(reporter) for reporter in reporters]
        goals = [objects.provide(goal) for goal in goals]

        return [os.environ.get("PYTHON", "python"), "-m", "flatsurvey.worker"] + list(chain(*[item.command() for item in [source] + goals + reporters]))

    async def _enqueue(self, command):
        r"""
        Run ``command`` once the load admits it.

        The result of this coroutine is a task that terminates when the command is completed.

        >>> scheduler = Scheduler(objects=[], goals=[], load=None)
        >>> asyncio.run(scheduler._enqueue(["true"]))
        <Task ...>

        """
        # TODO: This is a bit of a hack: Without it, the _run never actually
        # runs and we just enqueue forever (we do not need 1 for this, 0
        # works.) Without it, we schedule too many tasks but the load does not
        # go up quickly enough.
        await asyncio.sleep(1)
        from os import cpu_count, getloadavg
        while self._load is not None and getloadavg()[0] / cpu_count() > self._load:
            await asyncio.sleep(1)

        return asyncio.create_task(self._run(command))

    async def _run(self, command):
        r"""
        Run ``command``.

        >>> scheduler = Scheduler(objects=[], goals=[], load=None)
        >>> asyncio.run(scheduler._run(["echo", "hello world"]))
        hello world
        >>> asyncio.run(scheduler._run(["no-such-command"]))
        Traceback (most recent call last):
        ...
        plumbum.commands.processes.CommandNotFound: ...
        >>> asyncio.run(scheduler._run(["false"]))
        Traceback (most recent call last):
        ...
        plumbum.commands.processes.ProcessExecutionError: Unexpected exit code: ...

        """
        if self._dry_run:
            print(" ".join(command))
            return

        import sys
        import datetime
        import os.path
        from plumbum import local, BG
        from plumbum.commands.processes import ProcessExecutionError
        local.cwd.chdir(os.path.dirname(os.path.dirname(__file__)))
        print("spawning ", " ".join(command))

        start = datetime.datetime.now()
        task = local[command[0]].__getitem__(command[1:]) & BG(stdout=sys.stdout, stderr=sys.stderr)

        try:
            while not task.ready():
                await asyncio.sleep(1)
            print("*** completed ", command)
    
            if task.stdout:
                print("*** task produced output on stdout: ")
                print(task.stdout)
        except ProcessExecutionError as e:
            print("*** process crashed ", " ".join(command))
            print(e)
    
        print("*** terminated after %s wall time"%(datetime.datetime.now() - start,))
