r"""
Entrypoint to run surveys.

Execute this file with Python to see possible commands.

Typically, you invoke this providing some source(s) and some target(s), e.g.,
to compute the orbit closure of all quadrilaterals:
```
python survey ngons -n 4 orbit-closure
```
"""
#*********************************************************************
#  This file is part of flatsurf.
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
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click

from .sources import generators
from .targets import targets
from .services import Services
from .scheduler import Scheduler

@click.group(chain=True)
def survey():
    r"""
    Main command, runs a survey; specific survey sources and targets are
    registered automatically as subcommands.

    >>> from click.testing import CliRunner
    >>> CliRunner().invoke(survey)

    """


# Register sources and targets as subcommans of "survey".
for kind in [generators, targets]:
    for command in kind:
        survey.add_command(command)


@survey.resultcallback()
def process(commands):
    r"""
    Run the specified subcommands of ``survey``.

    >>> from click.testing import CliRunner
    >>> CliRunner().invoke(survey, ["--dry-run", "ngons", "-n", "4", "--limit", 6, "orbit-closure"]).output
    """
    sources = []
    targets = []
    for command in commands:
        from collections.abc import Iterable
        if isinstance(command, Iterable):
            sources.append(command)
        else:
            targets.append(command)

    Scheduler(sources, targets).start()


if __name__ == "__main__": survey()
