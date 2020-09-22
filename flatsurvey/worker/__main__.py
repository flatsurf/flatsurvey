r"""
Entrypoint for the survey worker to solve a single work package.

Invoke this providing a source and some goals, e.g., to compute the orbit closure of a quadrilateral:
```
python -m survey.worker ngon -a 1 -a 2 -a 3 -a 4 orbit-closure
```

# TODO: Improve command layout in usage with https://stackoverflow.com/a/57086581/812379

TESTS::
    
    >>> from ..test.cli import invoke
    >>> invoke(worker) # doctest: +NORMALIZE_WHITESPACE
    Usage: worker [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Main command to invoke the worker; specific objects and goals are
      registered automatically as subcommands.
    Options:
      --debug
      --help   Show this message and exit.
    Commands:
      completely-cylinder-periodic
      cylinder-periodic-direction
      ngon                          Construct an n-gon
      orbit-closure
      pickle                        Load a base64 encoded pickle

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

import click

import pdb

from ..objects import objects
from ..goals import goals
from ..reports import reporters, Report, Reporter, Log
from ..objects.surface import Surface
from ..pipeline import graph, provide

@click.group(chain=True)
@click.option("--debug", is_flag=True)
def worker(debug):
    r"""
    Main command to invoke the worker; specific objects and goals are
    registered automatically as subcommands.
    """


for kind in [objects, goals, reporters]:
    for command in kind:
        worker.add_command(command)


@worker.resultcallback()
def process(commands, debug):
    r"""
    Run the specified subcommands of ``worker``.

    >>> from ..test.cli import invoke
    >>> invoke(worker, "ngon", "-a", "1", "-a", "1", "-a", "1", "orbit-closure")

    """
    if debug: import pdb

    try:
      source = None
      goals = []
      reporters = []

      for command in commands:
          if isinstance(command, Surface):
              if source is not None:
                  raise ValueError("cannot process more than one source at once")
              source = command
          elif Reporter in command.mro():
              reporters.append(command)
          else:
              goals.append(command)

      if not reporters:
          reporters = [Log]

      objects = graph(
          provide('surface', lambda: source),
          provide('reporters', lambda: reporters),
          provide('goals', lambda: goals),
      )

      reporters = [objects.provide(reporter) for reporter in reporters]
      goals = [objects.provide(goal) for goal in goals]

      objects.provide(Worker).start()

      for reporter in reporters:
          reporter.flush()
    except:
        if debug:
            pdb.post_mortem()
        raise


class Worker:
    r"""
    Works on ``goals`` until they are all resolved.

    >>> Worker(Services(), [])
    Worker

    """
    def __init__(self, goals):
        self._goals = goals

    def  __repr__(self): return "Worker"

    def start(self):
        r"""
        Resolve all registered goals.

        >>> Worker(Services(), []).start()

        """
        for goal in self._goals:
            goal.resolve()

if __name__ == "__main__": worker()
