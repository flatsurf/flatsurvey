r"""
Entrypoint for the survey worker to solve a single work package.

Invoke this providing a source and some goals, e.g., to compute the orbit closure of a quadrilateral:
```
python -m survey.worker ngon -a 1 -a 2 -a 3 -a 4 orbit-closure
```

TESTS::
    
    >>> from ..test.cli import invoke
    >>> invoke(worker) # doctest: +NORMALIZE_WHITESPACE
    Usage: worker [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Explore a surface.
    Options:
      --debug
      --help   Show this message and exit.
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
      ngon            Unfolding of an n-gon with prescribed angles.
      pickle          A base64 encoded pickle.
      thurston-veech  Thurston-Veech construction

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2021 Julian Rüth
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
#*********************************************************************

import sys
import click
import pinject
import collections

import flatsurvey.surfaces
import flatsurvey.jobs
import flatsurvey.reporting
import flatsurvey.cache

from flatsurvey.pipeline import Consumer
from flatsurvey.pipeline.util import ListBindingSpec, FactoryBindingSpec
from flatsurvey.ui.group import CommandWithGroups
from flatsurvey.worker.restart import Restart

@click.group(chain=True, cls=CommandWithGroups, help=r"""Explore a surface.""")
@click.option("--debug", is_flag=True)
def worker(debug):
    r"""
    Main command to invoke the worker; specific objects and goals are
    registered automatically as subcommands.

    """


# Register subcommands
for kind in [flatsurvey.surfaces.commands, flatsurvey.jobs.commands, flatsurvey.reporting.commands, flatsurvey.cache.commands]:
    for command in kind:
        worker.add_command(command)


@worker.result_callback()
def process(commands, debug):
    r"""
    Run the specified subcommands of ``worker``.

    EXAMPLES:

    We compute the orbit closure of the unfolding of a equilateral triangle,
    i.e., the torus::

        >>> from ..test.cli import invoke
        >>> invoke(worker, "ngon", "-a", "1", "-a", "1", "-a", "1", "orbit-closure")
        [Ngon([1, 1, 1])] [FlowDecompositions] ¯\_(ツ)_/¯ (orientation: (-6, (-2*c ~ -3.4641016))) (cylinders: 1) (minimal: 0) (undetermined: 0)
        [Ngon([1, 1, 1])] [OrbitClosure] dimension: 2/2
        [Ngon([1, 1, 1])] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 2 in H_1(0) (ambient dimension 2) (dimension: 2) (directions: 1) (directions_with_cylinders: 1) (dense: True)

    """
    if debug:
        import pdb
        import signal
        signal.signal(signal.SIGUSR1, lambda sig, frame: pdb.Pdb().set_trace(frame))

    try:
        while True:
            objects = Worker.make_object_graph(commands)

            try:
                import asyncio
                asyncio.run(objects.provide(Worker).start())
            except Restart as restart:
                commands = [ restart.rewrite_command(command, objects=objects) for command in commands ]
                continue

            break
    except:
        if debug:
            pdb.post_mortem()
        raise


class Worker:
    r"""
    Works on a set of ``goals`` until they are all resolved.

    EXAMPLES::

        >>> import asyncio
        >>> worker = Worker(goals=[], reporters=[])
        >>> start = worker.start()
        >>> asyncio.run(start)

    """
    @pinject.copy_args_to_internal_fields
    def __init__(self, goals, reporters): pass

    @classmethod
    def make_object_graph(cls, commands):
        bindings = []
        goals = []
        reporters = []

        for command in commands:
            bindings.extend(command.get('bindings', []))
            goals.extend(command.get('goals', []))
            reporters.extend(command.get('reporters', []))

        bindings.append(ListBindingSpec("goals", goals))
        bindings.append(ListBindingSpec("reporters", reporters or [flatsurvey.reporting.Log]))
        from random import randint
        bindings.append(FactoryBindingSpec("lot", lambda: randint(0, 2**64)))

        return pinject.new_object_graph(modules=[flatsurvey.reporting, flatsurvey.surfaces, flatsurvey.jobs, flatsurvey.cache], binding_specs=bindings)

    async def start(self):
        r"""
        Run until all our goals are resolved.

        """
        try:
            # TODO: This is a weird hack.
            for goal in self._goals:
                await goal.init()
            for goal in self._goals:
                await goal.resolve()
        finally:
            for goal in self._goals:
                await goal.report()
        for reporter in self._reporters:
            reporter.flush()


if __name__ == "__main__": worker()
