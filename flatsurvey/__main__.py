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
      Main command, runs a survey; specific survey objects and goals are
      registered automatically as subcommands.
    Options:
      --dry-run
      --help     Show this message and exit.
    Commands:
      completely-cylinder-periodic
      cylinder-periodic-direction
      ngons                         Return all n-gons with the given...
      orbit-closure

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

from .objects import generators
from .goals import goals
from .reports import reporters, Reporter
from .scheduler import Scheduler
from .util.click.group import CommandWithGroups

@click.group(chain=True, cls=CommandWithGroups, help="Run a survey on the `objects` until all the `goals` are reached.")
@click.option('--dry-run', is_flag=True, help="do not spawn any workers")
def survey(dry_run):
    r"""
    Main command, runs a survey; specific survey objects and goals are
    registered automatically as subcommands.
    """


# Register objects and goals as subcommans of "survey".
for kind in [generators, goals, reporters]:
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
    goals = []
    reporters = []

    for command in commands:
        from collections.abc import Iterable
        if isinstance(command, Iterable):
            objects.append(command)
        elif Reporter in command.mro():
            reporters.append(command)
        else:
            goals.append(command)

    if kwargs.get('dry_run', False):
        kwargs.setdefault('load', None)

    asyncio.run(Scheduler(objects, goals, reporters, **kwargs).start())
    # import cProfile
    # print(cProfile.runctx("asyncio.run(Scheduler(objects, goals, reporters, **kwargs).start())", globals(), locals()))


if __name__ == "__main__": survey()
