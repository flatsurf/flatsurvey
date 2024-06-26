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
    <BLANKLINE>
      Run a survey on the `objects` until all the `goals` are reached.
    <BLANKLINE>
    Options:
      --debug
      --help               Show this message and exit.
      -N, --dry-run        Do not spawn any workers.
      -l, --load L         Do not start workers until load is below L.
      -q, --queue INTEGER  Jobs to prepare in the background for scheduling.
      -v, --verbose        Enable verbose message, repeat for debug message.
    <BLANKLINE>
    Cache:
      local-cache  A cache of previous results stored in local JSON files.
      pickles      Access a database of pickles storing parts of previous
                   computations.
    <BLANKLINE>
    Goals:
      completely-cylinder-periodic  Determines whether for all directions given by
                                    saddle connections, the decomposition of the
                                    surface is completely cylinder periodic, i.e.,
                                    the decomposition consists only of cylinders.
      cylinder-periodic-direction   Determines whether there is a direction for
                                    which the surface decomposes into cylinders.
      orbit-closure                 Determines the GL₂(R) orbit closure of
                                    ``surface``.
      undetermined-iet              Tracks undetermined Interval Exchange
                                    Transformations.
    <BLANKLINE>
    Intermediates:
      flow-decompositions             Turns directions coming from saddle
                                      connections into flow decompositions.
      saddle-connection-orientations  Orientations of saddle connections on the
                                      surface, i.e., the vectors of saddle
                                      connections irrespective of scaling and sign.
      saddle-connections              Saddle connections on the surface.
    <BLANKLINE>
    Reports:
      json      Writes results in JSON format.
      log       Writes progress and results as an unstructured log file.
      progress  Reports progress on the command line.
      report    Generic reporting of results.
    <BLANKLINE>
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

import click

import flatsurvey.cache
import flatsurvey.jobs
import flatsurvey.reporting
import flatsurvey.surfaces
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
@click.option(
    "--queue",
    "-q",
    type=int,
    default=128,
    help="Jobs to prepare in the background for scheduling.",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Enable verbose message, repeat for debug message.",
)
def survey(dry_run, load, debug, queue, verbose):
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
    # For technical reasons, queue needs to be a parameter here. It is consumed by process() below.
    _ = queue
    # For technical reasons, verbose needs to be a parameter here. It is consumed by process() below.
    _ = verbose


# Register objects and goals as subcommans of "survey".
for commands in [
    flatsurvey.cache.commands,
    flatsurvey.surfaces.generators,
    flatsurvey.reporting.commands,
    flatsurvey.jobs.commands,
]:
    for command in commands:
        survey.add_command(command)


@survey.result_callback()
def process(subcommands, dry_run=False, load=None, debug=False, queue=128, verbose=0):
    r"""
    Run the specified subcommands of ``survey``.

    EXAMPLES:

    We start an orbit-closure computation for a single triangle without waiting
    for the system load to be low::

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(survey, "--load=0", "ngons", "-n", "3", "--limit=3", "--literature=include", "orbit-closure")

    """
    if debug:
        import pdb
        import signal

        signal.signal(signal.SIGUSR1, lambda sig, frame: pdb.Pdb().set_trace(frame))

    if verbose:
        import logging

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG if verbose > 1 else logging.INFO)

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

        import asyncio
        import sys

        from flatsurvey.scheduler import Scheduler

        sys.exit(
            asyncio.new_event_loop().run_until_complete(
                Scheduler(
                    surface_generators,
                    bindings=bindings,
                    goals=goals,
                    reporters=reporters,
                    queue=queue,
                    dry_run=dry_run,
                    load=load,
                    debug=debug,
                ).start()
            )
        )
    except Exception:
        if debug:
            pdb.post_mortem()
        raise
