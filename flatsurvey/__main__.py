r"""
Entrypoint to run surveys.

Typically, you invoke this providing some source(s) and some target(s), e.g.,
to compute the orbit closure of all quadrilaterals:
```
python -m survey ngons -n 4 orbit-closure
```

TESTS::

    >>> from .test.cli import invoke
    >>> invoke(survey) # doctest: +NORMALIZE_WHITESPACE
    Usage: survey [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Run a survey on the `objects` until all the `goals` are reached.
    Options:
      --dry-run  do not spawn any workers
      --help     Show this message and exit.
    Cache:
      cache  A cache of previous results stored behind a GraphQL API in the cloud.
    Goals:
      completely-cylinder-periodic    Determines whether for all directions given by
                                      saddle connections, the decomposition of the
                                      surface is completely cylinder periodic, i.e.,
                                      the decomposition consists only of cylinders.
      completely-cylinder-periodic-asymptotics
                                      Determine the maximum circumference of all
                                      cylinders of length at most `R` in each
                                      completely cylinder periodic direction.
      cylinder-periodic-direction     Determines whether there is a direction for
                                      which the surface decomposes into cylinders.
      orbit-closure                   Determine the GL₂(R) orbit closure of
                                      ``surface``.
      undetermined-iet                Track undetermined Interval Exchang
                                      Transformations.
    Intermediates:
      flow-decompositions             Turns directions coming from saddle
                                      connections into flow decompositions.
      saddle-connection-orientations  Orientations of saddle connections on the
                                      surface, i.e., the vectors of saddle
                                      connections irrespective of scaling and sign.
      saddle-connections              Saddle connections on the surface.
    Reports:
      graphql  Reports results to our GraphQL cloud database.
      log      Writes progress and results as an unstructured log file.
      yaml     Writes results to a YAML file.
    Surfaces:
      ngons           The translation surfaces that come from unfolding n-gons.
      thurston-veech  The translation surfaces obtained from Thurston-Veech
                      construction.

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
import click
import flatsurvey

import flatsurvey.cache
import flatsurvey.jobs
import flatsurvey.reporting
import flatsurvey.surfaces

from flatsurvey.ui.group import CommandWithGroups

@click.group(chain=True, cls=CommandWithGroups, help="Run a survey on the `objects` until all the `goals` are reached.")
@click.option('--dry-run', is_flag=True, help="do not spawn any workers")
def survey(dry_run):
    r"""
    Main command, runs a survey; specific survey objects and goals are
    registered automatically as subcommands.
    """


# Register objects and goals as subcommans of "survey".
for kind in [flatsurvey.surfaces.generators, flatsurvey.jobs.commands, flatsurvey.reporting.commands, flatsurvey.cache.commands]:
    for command in kind:
        survey.add_command(command)


@survey.result_callback()
def process(commands, **kwargs):
    r"""
    Run the specified subcommands of ``survey``.

    # TODO: Currently, pytest fails to test these with a "fileno" error.
    # >>> from .test.cli import invoke
    # >>> invoke(survey, "ngons", "-n", "3", "--include-literature", "--limit", "4", "orbit-closure")

    """
    surface_generators = []
    goals = []
    reporters = []
    bindings = []

    for command in commands:
        from collections.abc import Iterable
        if isinstance(command, dict):
            goals.extend(command.get('goals', []))
            reporters.extend(command.get('reporters', []))
            bindings.extend(command.get('bindings', []))
        else:
            surface_generators.append(command)

    if kwargs.get('dry_run', False):
        kwargs.setdefault('load', None)

    asyncio.run(Scheduler(surface_generators, bindings=bindings, goals=goals, reporters=reporters, **kwargs).start())


class Scheduler:
    r"""
    A simple scheduler that splits a survey into commands that are run on the local
    machine when the load admits it.

    >>> Scheduler(generators=[], bindings=[], goals=[], reporters=[])
    Scheduler

    """
    def __init__(self, generators, bindings, goals, reporters, dry_run=False, load=1., quiet=False):
        self._generators = generators
        self._bindings = bindings
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

        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[])
        >>> asyncio.run(scheduler.start())
        All jobs have been scheduled. Now waiting for jobs to finish.

        """
        tasks = []
        nothing = object()
        from itertools import zip_longest, chain
        iters = [iter(generator) for generator in self._generators]
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

        print("All jobs have been scheduled. Now waiting for jobs to finish.")
        await asyncio.gather(*tasks)

    async def _render_command(self, surface):
        r"""
        Return the command to invoke a worker to compute the ``goals`` for ``surface``.

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.jobs import OrbitClosure

        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[OrbitClosure], reporters=[])
        >>> scheduler._render_command(Ngon([1, 1, 1])) # doctest: +ELLIPSIS
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
        objects = pinject.new_object_graph(modules=[flatsurvey.reporting, flatsurvey.surfaces, flatsurvey.jobs, flatsurvey.cache], binding_specs=bindings)

        commands = []

        class Reporters:
            def __init__(self, reporters): self._reporters = reporters
        for reporter in objects.provide(Reporters)._reporters:
            commands.extend(reporter.command())

        class Goals:
            def __init__(self, goals): self._goals = goals
        goals = [goal for goal in objects.provide(Goals)._goals if goal._resolved != goal.COMPLETED]
        if not goals:
            print(f"No goals left for {surface}. Skipping.")
            return None
        for goal in goals:
            commands.extend(goal.command())

        commands.extend(surface.command())

        import os
        return [os.environ.get("PYTHON", "python"), "-m", "flatsurvey.worker"] + commands

    async def _enqueue(self, command):
        r"""
        Run ``command`` once the load admits it.

        The result of this coroutine is a task that terminates when the command is completed.

        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[], load=None)
        >>> asyncio.run(scheduler._enqueue(["true"]))
        spawning true
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

        # TODO: Currently, pytest fails to test these with a "fileno" error.
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
                print(" ".join(command))
            return

        import sys
        import datetime
        import os.path
        from plumbum import local, BG
        from plumbum.commands.processes import ProcessExecutionError
        local.cwd.chdir(os.path.dirname(os.path.dirname(__file__)))
        print("spawning", " ".join(command))

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

if __name__ == "__main__": survey()
