r"""
Entrypoint to run surveys.

Typically, you invoke this providing some source(s) and some target(s), e.g.,
to compute the orbit closure of all quadrilaterals:
```
python -m survey ngons -n 4 orbit-closure
```

TESTS::

    >>> from flatsurvey.test.cli import invoke
    >>> invoke(survey) # doctest: +NORMALIZE_WHITESPACE
    Usage: survey [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Run a survey on the `objects` until all the `goals` are reached.
    Options:
      --help         Show this message and exit.
      -N, --dry-run  Do not spawn any workers.
      -l, --load L   Do not start workers until load is below L.
    Cache:
      cache  A cache of previous results stored behind a GraphQL API in the cloud.
    Goals:
      completely-cylinder-periodic   Determines whether for all directions given by
                                     saddle connections, the decomposition of the
                                     surface is completely cylinder periodic, i.e.,
                                     the decomposition consists only of cylinders.
      cylinder-periodic-asymptotics  Determines the maximum circumference of all
                                     cylinders in each cylinder periodic direction.
      cylinder-periodic-direction    Determines whether there is a direction for
                                     which the surface decomposes into cylinders.
      orbit-closure                  Determines the GL₂(R) orbit closure of
                                     ``surface``.
      undetermined-iet               Tracks undetermined Interval Exchange
                                     Transformations.
    Intermediates:
      boshernitzan-conjecture-orientations
                                      Produces some particular directions in
                                      triangles related to a conjecture of
                                      Boshernitzan.
      flow-decompositions             Turns directions coming from saddle
                                      connections into flow decompositions.
      saddle-connection-orientations  Orientations of saddle connections on the
                                      surface, i.e., the vectors of saddle
                                      connections irrespective of scaling and sign.
      saddle-connections              Saddle connections on the surface.
    Reports:
      graphql  Reports results to our GraphQL cloud database.
      log      Writes progress and results as an unstructured log file.
      report   Generic reporting of results.
      yaml     Writes results to a YAML file.
    Surfaces:
      ngons           The translation surfaces that come from unfolding n-gons.
      thurston-veech  The translation surfaces obtained from Thurston-Veech
                      construction.

"""
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

import asyncio
import os
import logging

import click

import flatsurvey
import flatsurvey.cache
import flatsurvey.jobs
import flatsurvey.reporting
import flatsurvey.surfaces
from flatsurvey.pipeline.util import provide
from flatsurvey.ui.group import CommandWithGroups


@click.group(
    chain=True,
    cls=CommandWithGroups,
    help="Run a survey on the `objects` until all the `goals` are reached.",
)
@click.option("--dry-run", "-N", is_flag=True, help="Do not spawn any workers.")
@click.option("--debug", is_flag=True)
@click.option(
    "--load",
    "-l",
    metavar="L",
    type=float,
    default=None,
    help="Do not start workers until load is below L.",
)
def survey(dry_run, load, debug):
    r"""
    Main command, runs a survey; specific survey objects and goals are
    registered automatically as subcommands.
    """
    # For technical reasons, dry_run needs to be a parameter here. It is consumed by process() below.
    _ = dry_run
    # For technical reasons, load needs to be a parameter here. It is consumed by process() below.
    _ = load
    # For technical reasons, debug needs to be a parameter here. It is consumed by process() below.
    _ = debug


# Register objects and goals as subcommans of "survey".
for commands in [
    flatsurvey.surfaces.generators,
    flatsurvey.jobs.commands,
    flatsurvey.reporting.commands,
    flatsurvey.cache.commands,
]:
    for command in commands:
        survey.add_command(command)


@survey.result_callback()
def process(subcommands, dry_run=False, load=None, debug=False):
    r"""
    Run the specified subcommands of ``survey``.

    EXAMPLES:

    We start an orbit-closure computation for a single triangle without waiting
    for the system load to be low::

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(survey, "--load=0", "ngons", "-n", "3", "--limit=3", "--literature=include", "orbit-closure")  # doctest: +ELLIPSIS
        All jobs have been scheduled. Now waiting for jobs to finish.
        ...
        [Ngon([1, 1, 1])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2) (dimension: 2) (directions: 1) (directions_with_cylinders: 1) (dense: True)
        ...

    """
    if debug:
        import pdb
        import signal

        signal.signal(signal.SIGUSR1, lambda sig, frame: pdb.Pdb().set_trace(frame))

    try:
        surface_generators = []
        goals = []
        reporters = []
        bindings = []

        for subcommand in subcommands:
            if isinstance(subcommand, dict):
                goals.extend(subcommand.get("goals", []))
                reporters.extend(subcommand.get("reporters", []))
                bindings.extend(subcommand.get("bindings", []))
            else:
                surface_generators.append(subcommand)

        if dry_run:
            load = 0

        asyncio.run(
            Scheduler(
                surface_generators,
                bindings=bindings,
                goals=goals,
                reporters=reporters,
                dry_run=dry_run,
                load=load,
                debug=debug,
            ).start()
        )
    except Exception:
        if debug:
            pdb.post_mortem()
        raise


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

        >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[])
        >>> asyncio.run(scheduler.start())
        All jobs have been scheduled. Now waiting for jobs to finish.

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
                object = provide(binding.name, objects)
                from flatsurvey.pipeline.util import FactoryBindingSpec
                return FactoryBindingSpec(binding.name, lambda: object)

            return binding

        self._bindings = [share(binding) for binding in self._bindings]

    async def _render_command(self, surface):
        r"""
        Return the command to invoke a worker to compute the ``goals`` for ``surface``.

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

            >>> scheduler = Scheduler(generators=[], bindings=[], goals=[], reporters=[], load=0)
            >>> asyncio.run(scheduler._enqueue(["true"]))
            ...
            <Task ...>

        """
        # This is a bit of a hack: Without it, the _run never actually
        # runs and we just enqueue forever (we do not need 1 for this, 0
        # works.) Without it, we schedule too many tasks but the load does not
        # go up quickly enough. See #5.
        await asyncio.sleep(1)

        if self._load > 0:
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
                await asyncio.sleep(1)

            if task.stdout:
                # We should have better monitoring, see #41.
                logging.warning("Task produced output on stdout:\n" + task.stdout)
        except ProcessExecutionError as e:
            # We should have better monitoring, see #41.
            logging.error("Process crashed: " + " ".join(command) + "\n" + str(e))


if __name__ == "__main__":
    survey()
