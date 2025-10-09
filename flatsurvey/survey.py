r"""
Entrypoint to run surveys.

Typically, you invoke this providing some sources and some goals, e.g., to
compute the orbit closure of all quadrilaterals:
```
flatsurvey ngons --vertices 4 orbit-closure
```

TESTS::

    >>> from flatsurvey.test.cli import invoke
    >>> invoke(survey)  # doctest: +NORMALIZE_WHITESPACE
    Usage: survey [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Run a survey on the `objects` until all the `goals` are reached.
    Options:
      --debug
      --mem-limit TEXT   Gracefully stop a worker's current task when the memory
                         consumption exceeds this amount
      --time-limit TEXT  Gracefully stop a worker's current task when the wall time
                         elapsed exceeds this amount
      --queue INTEGER    Jobs to prepare in the background for scheduling. [default:
                         3 × cores]
      -v, --verbose      Enable verbose message, repeat for debug message.
      --quiet            Silence all terminal output
      --scheduler TEXT   Path to a dask scheduler file
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
      ngons  The translation surfaces that come from unfolding n-gons.

We compute orbit closures of a few triangles::

    >>> invoke(survey, "orbit-closure", "ngons", "--vertices", "3", "--count", "3")
    waiting for jobs to finish |████████████████████████████████████████| 3 in ...

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
from flatsurvey.ui.group import CommandWithGroups

# Whether the current process is running the survey scheduler.
# Used for memory leak prevention by not instantiating leaky objects in the
# scheduler.
IS_SURVEY_ORCHESTRATOR = False


@click.group(
    chain=True,
    cls=CommandWithGroups,
    help="Run a survey on the `objects` until all the `goals` are reached.",
)
@click.option("--debug", is_flag=True)
@click.option(
    "--mem-limit",
    default=None,
    help="Gracefully stop a worker's current task when the memory consumption exceeds this amount",
)
@click.option(
    "--time-limit",
    default=None,
    help="Gracefully stop a worker's current task when the wall time elapsed exceeds this amount",
)
@click.option(
    "--queue",
    type=int,
    default=None,
    help="Jobs to prepare in the background for scheduling. [default: 3 × cores]",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Enable verbose message, repeat for debug message.",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Silence all terminal output",
)
@click.option(
    "--scheduler",
    default=None,
    type=str,
    help="Path to a dask scheduler file",
)
def survey(debug, mem_limit, time_limit, queue, verbose, quiet, scheduler):
    r"""
    Main command, runs a survey; specific survey objects and goals are
    registered automatically as subcommands.
    """
    del debug  # handled by process()
    del mem_limit  # handled by process()
    del time_limit  # handled by process()
    del queue  # handled by process()
    del verbose  # handled by process()
    del quiet  # handled by process()
    del scheduler  # handled by process()


# Register objects and goals as subcommands of "survey".
for commands in [
    flatsurvey.cache.commands,
    flatsurvey.surfaces.generators,
    flatsurvey.reporting.commands,
    flatsurvey.jobs.commands,
]:
    for command in commands:
        survey.add_command(command)


@survey.result_callback()
def process(
    subcommands,
    debug=False,
    mem_limit=None,
    time_limit=None,
    queue=None,
    verbose=0,
    quiet=False,
    scheduler=None,
):
    r"""
    Run the specified subcommands of ``survey``.

    EXAMPLES:

    We start an orbit-closure computation for a single triangle::

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(survey, "ngons", "-n", "3", "--limit=3", "--literature=include", "orbit-closure")  # random progress output
        waiting for jobs to finish |████████████████████████████████████████| 1 in ...

    """
    import pdb

    if debug:
        import signal

        signal.signal(signal.SIGUSR1, lambda _, frame: pdb.Pdb().set_trace(frame))

    if verbose:
        import logging

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG if verbose > 1 else logging.INFO)

    if quiet:
        import logging

        logger = logging.getLogger()
        logger.setLevel(logging.FATAL)

    if mem_limit is not None:
        from flatsurvey.dask.limits import MemoryLimit

        mem_limit = MemoryLimit(mem_limit)

    if time_limit is not None:
        from flatsurvey.dask.limits import TimeLimit

        time_limit = TimeLimit(time_limit)

    global IS_SURVEY_ORCHESTRATOR
    IS_SURVEY_ORCHESTRATOR = True
    try:
        from flatsurvey.pipeline import Bindings

        bindings = Bindings()

        for subcommand in subcommands:
            subcommand(bindings)

        import asyncio
        import sys

        from flatsurvey.dask import Scheduler
        from flatsurvey.ui.progress import Progress

        with Progress.create(stdout=not quiet) as progress:
            sys.exit(
                asyncio.new_event_loop().run_until_complete(
                    Scheduler(
                        survey_bindings=bindings.survey_bindings,
                        mem_limit=mem_limit,
                        time_limit=time_limit,
                        queue_limit=queue,
                        scheduler_json=scheduler,
                        progress=progress,
                    ).start()
                )
            )
    except Exception:
        if debug:
            pdb.post_mortem()
        raise
    finally:
        IS_SURVEY_ORCHESTRATOR = False
