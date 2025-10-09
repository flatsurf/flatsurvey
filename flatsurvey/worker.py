r"""
Entrypoint for the survey worker to solve a single work package.

Invoke this providing a source and some goals, e.g., to compute the orbit
closure of a quadrilateral:
```
flatsurvey-worker ngon -a 1 -a 2 -a 3 -a 4 orbit-closure
```

TESTS::

    >>> from flatsurvey.test.cli import invoke
    >>> invoke(worker) # doctest: +NORMALIZE_WHITESPACE
    Usage: worker [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Explore a surface.
    Options:
      --debug
      --mem-limit TEXT   Gracefully stop the worker's current task when the memory
                         consumption exceeds this amount
      --time-limit TEXT  Gracefully stop the worker's current task when the wall
                         time elapsed exceeds this amount
      -v, --verbose      Enable verbose message, repeat for debug message.
      --help             Show this message and exit.
    Cache:
      local-cache  A readonly cache of previous results, read from local JSON...
      pickles      Provide pickle files as referenced in the caches.
    Goals:
      completely-cylinder-periodic  Determines whether for all directions given...
      cylinder-periodic-direction   Determines whether there is a direction for...
      orbit-closure                 Determines the GL₂(R) orbit closure of...
      undetermined-iets             Tracks undetermined Interval Exchange...
    Intermediates:
      flow-decompositions             Turns directions coming from saddle...
      saddle-connection-orientations  Orientations of saddle connections on the...
      saddle-connections              Saddle connections on the surface.
    Reports:
      json    Writes results in JSON format.
      log     Writes progress and results as an unstructured log file.
      report  Generic reporting of results.
    Surfaces:
      ngon  Unfolding of an n-gon with prescribed angles.

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

import click

import flatsurvey.cache
import flatsurvey.jobs
import flatsurvey.reporting
import flatsurvey.surfaces
from flatsurvey.dask.limits import Limit
from flatsurvey.pipeline import BindingException, Bindings, Consumer, Goal
from flatsurvey.reporting.report import Report
from flatsurvey.ui.group import CommandWithGroups


@click.group(
    chain=True,
    cls=CommandWithGroups,
    help=r"""Explore a surface.""",
)
@click.option("--debug", is_flag=True)
@click.option(
    "--mem-limit",
    default=None,
    help="Gracefully stop the worker's current task when the memory consumption exceeds this amount",
)
@click.option(
    "--time-limit",
    default=None,
    help="Gracefully stop the worker's current task when the wall time elapsed exceeds this amount",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Enable verbose message, repeat for debug message.",
)
def worker(debug, mem_limit, time_limit, verbose):
    r"""
    Main command to invoke the worker; specific objects and goals are
    registered automatically as subcommands.
    """
    del debug  # handled by process()
    del mem_limit  # handled by process()
    del time_limit  # handled by process()
    del verbose  # handled by process()


# Register subcommands
for kind in [
    flatsurvey.surfaces.commands,
    flatsurvey.jobs.commands,
    flatsurvey.reporting.commands,
    flatsurvey.cache.commands,
]:
    for command in kind:
        worker.add_command(command)


@worker.result_callback()
def process(commands, debug, mem_limit, time_limit, verbose):
    r"""
    Run the specified subcommands of ``worker``.

    EXAMPLES:

    We compute the orbit closure of the unfolding of a equilateral triangle,
    i.e., the torus::

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(worker, "ngon", "-a", "1", "-a", "1", "-a", "1", "orbit-closure")
        [OrbitClosure] dimension: 2/2
        [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2) (dimension: 2) (dimension_upper_bound: 2) (directions: 1) (directions_with_cylinders: 1) (dense: True) (stratum: H_1(0))

    """
    import pdb

    if debug:
        import signal

        signal.signal(signal.SIGUSR1, lambda _, frame: pdb.Pdb().set_trace(frame))

    if verbose:
        import logging

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG if verbose > 1 else logging.INFO)

    from flatsurvey.pipeline import Bindings

    bindings = Bindings()

    for command in commands:
        command(bindings)

    limits = []
    if mem_limit is not None:
        from flatsurvey.dask.limits import MemoryLimit

        limits.append(MemoryLimit(mem_limit))

    if time_limit is not None:
        from flatsurvey.dask.limits import TimeLimit

        limits.append(TimeLimit(time_limit))

    try:
        import asyncio

        from flatsurvey.reporting import Log, Reporter

        # Inject a default reporter to stdout if none is configured yet.
        try:
            bindings.get(list[Reporter])
        except BindingException:
            bindings.append(list[Reporter], Log(output="-"))

        asyncio.run(Worker.work(bindings=bindings, limits=limits))
    except Exception:
        if debug:
            pdb.post_mortem()
        raise


class Worker:
    r"""
    Works on a set of ``goals`` until they are all resolved.

    Instances of this class should not be created directly. Use :meth:`work`
    instead.

    """

    def __init__(
        self,
        goals: list[Goal],
        report: Report,
    ):
        self._goals = goals
        self._report = report

    @classmethod
    async def work(cls, /, bindings: Bindings, limits: list[Limit] | None = None):
        r"""
        Create a :class:`Worker` and use it to resolve the goals defined by
        ``bindings``.

        INPUT:

        - ``bindings`` -- bindings whose ``list[Goal]`` entry specifies the
          tasks that should be resolved.

        - ``limits`` -- a list of :class:`Limit` resource checks that abort all
          computations when the limits are exceeded.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.jobs import OrbitClosure
            >>> from flatsurvey.pipeline import Bindings, Goal
            >>> from flatsurvey.reporting import Log, Reporter

            >>> bindings = Bindings()
            >>> bindings.define(Surface, Ngon(angles=[1, 1, 1]))
            >>> bindings.append(list[Goal], OrbitClosure)
            >>> bindings.append(list[Reporter], Log(output="-"))

            >>> import asyncio
            >>> asyncio.run(Worker.work(bindings))
            [OrbitClosure] dimension: 2/2
            [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2) (dimension: 2) (dimension_upper_bound: 2) (directions: 1) (directions_with_cylinders: 1) (dense: True) (stratum: H_1(0))

        When the computation raises a restart exception, it restarts with the
        modified bindings automatically::

            >>> bindings = Bindings()
            >>> bindings.define(Surface, Ngon(angles=[1, 4, 11]))
            >>> bindings.append(list[Goal], OrbitClosure)
            >>> with bindings.scope(OrbitClosure) as scoped: scoped.define(deform_limit=0, limit=32)
            >>> bindings.append(list[Reporter], Log(output="-"))

            >>> import asyncio
            >>> asyncio.run(Worker.work(bindings))  # doctest: +ELLIPSIS
            [OrbitClosure] dimension: 3/8
            [OrbitClosure] Found 0 directions with cylinders without a dimension increase. Will attempt to deform the surface to improve the situation.
            ...
            [OrbitClosure] GL(2,R)-orbit closure of dimension at least ... in H_6(10) ... (dense: None) (stratum: H_6(10))

        """
        from flatsurvey.restart import Restart

        worker = Worker(goals=bindings.get(list[Goal], []), report=bindings.get(Report))

        try:
            await worker._start(limits=limits)
        except Restart as restart:
            import logging

            logger = logging.getLogger()
            logger.info("Performing restart")

            await Worker.work(bindings=restart.create_bindings(bindings), limits=limits)

    async def _start(self, limits: list[Limit] | None = None):
        r"""
        Run until all our goals are resolved.

        Helper method for :meth:`work`.

        EXAMPLES::

            >>> import asyncio
            >>> from flatsurvey.reporting.report import Report
            >>> worker = Worker(goals=[], report=Report(reporters=[]))
            >>> asyncio.run(worker._start())

        """
        limits = limits or []

        def callback():
            for goal in self._goals:
                goal._resolved = True

        from flatsurvey.dask.limits import LimitChecker

        checks = [LimitChecker(limit, callback) for limit in limits]

        for check in checks:
            check.start()

        try:
            try:
                for goal in self._goals:
                    if isinstance(goal, Consumer):
                        await goal.consume_cache()
                for goal in self._goals:
                    await goal.resolve()
            finally:
                for goal in self._goals:
                    if isinstance(goal, Consumer):
                        await goal.report()
        finally:
            for check in checks:
                check.stop()

        self._report.flush()
