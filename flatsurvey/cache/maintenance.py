r"""
Entrypoint to organize .JSON files written by surveys.

TESTS::

    >>> from flatsurvey.test.cli import invoke
    >>> invoke(cli) # doctest: +NORMALIZE_WHITESPACE
    Usage: cli [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
    <BLANKLINE>
      Mangle cache files.
    <BLANKLINE>
    Options:
      --debug
      --help         Show this message and exit.
      -v, --verbose  Enable verbose message, repeat for debug message.
    <BLANKLINE>
    Commands:
      join
      split

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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
import pinject

from flatsurvey.ui.group import CommandWithGroups
from flatsurvey.cache.split import Split
from flatsurvey.cache.join import Join
from flatsurvey.pipeline.util import ListBindingSpec, FactoryBindingSpec
import flatsurvey.reporting.log


@click.group(
    chain=True,
    cls=CommandWithGroups,
    help=r"""Mangle cache files.""",
)
@click.option("--debug", is_flag=True)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Enable verbose message, repeat for debug message.",
)
def cli(debug, verbose):
    r"""
    Performs maintenance tasks on collections of .JSON files.

    Specific tasks are registered as subcommands.
    """


cli.add_command(Split.click)
cli.add_command(Join.click)


@cli.result_callback()
def process(commands, debug, verbose):
    r"""
    Run the specified subcommands of ``cli``.

    EXAMPLES:

    TODO
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
        objects = Maintenance.make_object_graph(commands)

        import asyncio
        asyncio.run(objects.provide(Maintenance).start())
    except Exception:
        if debug:
            pdb.post_mortem()
        raise


class Maintenance:
    """
    TODO: Document me. This is essentially a clone of Worker.
    """
    @pinject.copy_args_to_internal_fields
    def __init__(self, goals, reporters): pass

    @classmethod
    def make_object_graph(cls, commands):
        bindings = []
        goals = []
        reporters = []

        for command in commands:
            bindings.extend(command.get("bindings", []))
            goals.extend(command.get("goals", []))
            reporters.extend(command.get("reporters", []))

        bindings.append(ListBindingSpec("goals", goals))
        bindings.append(
            ListBindingSpec("reporters", reporters or [flatsurvey.reporting.Log])
        )
        bindings.append(
            FactoryBindingSpec("surface", lambda: None)
        )

        return pinject.new_object_graph(
            modules=[
                flatsurvey.reporting,
                flatsurvey.cache.maintenance
            ],
            binding_specs=bindings,
            allow_injecting_none=True,
        )

    async def start(self):
        r"""
        Run until all our goals are resolved.
        """
        try:
            for goal in self._goals:
                await goal.consume_cache()
            for goal in self._goals:
                await goal.resolve()
        finally:
            for goal in self._goals:
                await goal.report()
        for reporter in self._reporters:
            reporter.flush()
