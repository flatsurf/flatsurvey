r"""
Entrypoint to organize .json files written by surveys.

TESTS::

    >>> from flatsurvey.test.cli import invoke
    >>> invoke(cli)  # doctest: +NORMALIZE_WHITESPACE
    Usage: cli [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
      Mangle cache files.
    Options:
      --debug
      -v, --verbose  Enable verbose message, repeat for debug message.
      --help         Show this message and exit.
    Commands:
      join  Aggregates JSON files into one file for each type of result.
    Reports:
      log  Writes progress and results as an unstructured log file.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022-2025 Julian Rüth
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
from flatsurvey.ui import CommandWithGroups


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
    del debug  # handled by process()
    del verbose  # handled by process()


for command in flatsurvey.cache.maintenance_commands:
    cli.add_command(command)


@cli.result_callback()
def process(commands, debug, verbose):
    r"""
    Run the specified subcommands of ``cli``.

    EXAMPLES:

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(cli, "join", "--help")  # doctest: +NORMALIZE_WHITESPACE
        Usage: cli join [OPTIONS] [JSONS]...
          Aggregates JSON files into one file for each type of result.
        Options:
          --outdir PATH  a directory to write the output files to  [required]
          --help         Show this message and exit.

    """
    if debug:
        import pdb
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

    try:
        import asyncio

        from flatsurvey.worker import Worker

        asyncio.run(Worker.work(bindings=bindings, limits=[]))
    except Exception:
        if debug:
            import pdb

            pdb.post_mortem()
        raise
