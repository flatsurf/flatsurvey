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
      Explore a surface.
    Options:
      --debug
      --help   Show this message and exit.
    Goals:
      completely-cylinder-periodic  Determine whether for all directions given by
                                    saddle connections, the decomposition of the
                                    surface is completely cylinder periodic, i.e.,
                                    the decomposition consists only of cylinders.
      cylinder-periodic-direction   Determine whether there is a direction for which
                                    the surface decomposes into cylinders.
      orbit-closure                 Determine the GL₂(R) orbit closure.
    Reports:
      dynamodb  Report results to the DynamoDB cloud database.
      log       Write results and progress to a log file.
      yaml      Write results to a YAML file.
    Surfaces:
      ngon    Unfolding of an n-gon with prescribed angles.
      pickle  A base64 encoded pickle.

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

import sys
import click
import pinject
import collections

import flatsurvey.surfaces
import flatsurvey.jobs
import flatsurvey.reporting

from flatsurvey.pipeline import Consumer
from flatsurvey.pipeline.util import ListBindingSpec, FactoryBindingSpec
from flatsurvey.ui.group import CommandWithGroups

@click.group(chain=True, cls=CommandWithGroups, help=r"""Explore a surface.""")
@click.option("--debug", is_flag=True)
def worker(debug):
    r"""
    Main command to invoke the worker; specific objects and goals are
    registered automatically as subcommands.

    >>> from ..test.cli import invoke
    >>> invoke(worker)

    """


# Register subcommands
for kind in [flatsurvey.surfaces.commands, flatsurvey.jobs.commands, flatsurvey.reporting.commands]:
    for command in kind:
        worker.add_command(command)


@worker.resultcallback()
def process(commands, debug):
    r"""
    Run the specified subcommands of ``worker``.

    EXAMPLES:

    We compute the orbit closure of the unfolding of a equilateral triangle,
    i.e., the torus::

    >>> from ..test.cli import invoke
    >>> invoke(worker, "ngon", "-a", "1", "-a", "1", "-a", "1", "orbit-closure")
    [Ngon(1, 1, 1)] [OrbitClosure] dimension: 2/2

    """
    if debug:
        import pdb

    try:
        bindings = dict(collections.ChainMap({}, *commands))

        binding_specs = list(bindings.values())
        binding_specs.append(ListBindingSpec("goals",
            [cls for cls in bindings.keys() if Consumer in cls.mro()]))
        binding_specs.append(ListBindingSpec("reporters",
            [cls for cls in bindings.keys() if flatsurvey.reporting.report.Reporter in cls.mro()] or [flatsurvey.reporting.Log]))
        binding_specs.append(FactoryBindingSpec("lot", lambda: randint(0, 2**64)))

        objects = pinject.new_object_graph(modules=[flatsurvey.reporting, flatsurvey.surfaces, flatsurvey.jobs], binding_specs=binding_specs)

        worker = objects.provide(Worker)
        worker.start()

    except:
        if debug:
            pdb.post_mortem()
        raise


class Worker:
    r"""
    Works on a set of ``goals`` until they are all resolved.

    EXAMPLES::

    >>> goals = [flatsurvey.goals.Trivial()]
    >>> worker = Worker(goals=goals, reporters=[])
    >>> worker.start()

    """
    @pinject.copy_args_to_internal_fields
    def __init__(self, goals, reporters): pass

    def start(self):
        r"""
        Run until all our goals are resolved.

        """
        for goal in self._goals:
            goal.resolve()
        for goal in self._goals:
            goal.report()
        for reporter in self._reporters:
            reporter.flush()


if __name__ == "__main__": worker()
