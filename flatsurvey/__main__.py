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
    Goals:
      completely-cylinder-periodic  Determines whether for all directions given by
                                    saddle connections, the decomposition of the
                                    surface is completely cylinder periodic, i.e.,
                                    the decomposition consists only of cylinders.
      cylinder-periodic-direction   Determines whether there is a direction for
                                    which the surface decomposes into cylinders.
      orbit-closure                 Determine the GL₂(R) orbit closure of
                                    ``surface``.
    Intermediates:
      flow-decompositions             Turns directions coming from saddle
                                      connections into flow decompositions.
      saddle-connection-orientations  Orientations of saddle connections on the
                                      surface, i.e., the vectors of saddle
                                      connections irrespective of scaling and sign.
      saddle-connections              Saddle connections on the surface.
    Reports:
      dynamodb  Reports results to Amazon's DynamoDB cloud database.
      log       Writes progress and results as an unstructured log file.
      yaml      Writes results to a YAML file.
    Surfaces:
      ngons  The translation surfaces that come from unfolding n-gons.

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

from flatsurvey.surfaces import generators
from flatsurvey.jobs import commands as jobs
from flatsurvey.reporting import commands as reporters, Reporter
from flatsurvey.worker.scheduler import Scheduler
from flatsurvey.ui.group import CommandWithGroups

@click.group(chain=True, cls=CommandWithGroups, help="Run a survey on the `objects` until all the `goals` are reached.")
@click.option('--dry-run', is_flag=True, help="do not spawn any workers")
def survey(dry_run):
    r"""
    Main command, runs a survey; specific survey objects and goals are
    registered automatically as subcommands.
    """


# Register objects and goals as subcommans of "survey".
for kind in [generators, jobs, reporters]:
    for command in kind:
        survey.add_command(command)


@survey.resultcallback()
def process(commands, **kwargs):
    r"""
    Run the specified subcommands of ``survey``.

    >>> from .test.cli import invoke
    >>> invoke(survey, "ngons", "-n", "3", "--include-literature", "--limit", "4", "orbit-closure")

    """
    objects = []
    jobs = []
    reporters = []

    for command in commands:
        from collections.abc import Iterable
        if isinstance(command, Iterable):
            objects.append(command)
        elif Reporter in command.mro():
            reporters.append(command)
        else:
            jobs.append(command)

    if kwargs.get('dry_run', False):
        kwargs.setdefault('load', None)

    asyncio.run(Scheduler(objects, jobs, reporters, **kwargs).start())


if __name__ == "__main__": survey()
