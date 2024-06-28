r"""
Writes progress and results as an unstructured log file.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "log", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker log [OPTIONS]
      Writes progress and results as an unstructured log file.
    Options:
      --output FILE      [default: stdout]
      --prefix DIRECTORY
      --help             Show this message and exit.

"""
# *********************************************************************
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
# *********************************************************************

import click
from pinject import copy_args_to_internal_fields, BindingSpec

from flatsurvey.command import Command
from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui.group import GroupedCommand


class Log(Reporter, Command):
    r"""
    Writes progress and results as an unstructured log file.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> log = Log(surface)
        >>> log.log(source=surface, message="Hello World")
        [Ngon([1, 1, 1])] [Ngon] Hello World

    """

    @copy_args_to_internal_fields
    def __init__(self, surface, stream=None):
        import sys

        self._stream = stream or sys.stdout

    def _prefix(self, source):
        return f"[{self._surface}] [{type(source).__name__}]"

    def _log(self, message):
        self._stream.write("%s\n" % (message,))
        self._stream.flush()

    def log(self, source, message, **kwargs):
        r"""
        Write a ``message`` to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log(surface)
            >>> log.log(source=surface, message="Hello World", extra="data", lot="1337")
            [Ngon([1, 1, 1])] [Ngon] Hello World (extra: data) (lot: 1337)

        """
        message = f"{self._prefix(source)} {message}"
        for k, v in kwargs.items():
            message += f" ({k}: {v})"
        self._log(message)

    @classmethod
    @click.command(
        name="log",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--output",
        type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
        default=None,
        help="[default: stdout]",
    )
    @click.option(
        "--prefix",
        type=click.Path(exists=True, file_okay=False, dir_okay=True, allow_dash=False),
        default=None,
    )
    def click(output, prefix):
        return {
            "bindings": Log.bindings(output=output, prefix=prefix),
            "reporters": [Log],
        }

    @classmethod
    def bindings(cls, output, prefix=None):
        return [
            LogBindingSpec(output=output, prefix=prefix)
        ]

    def deform(self, deformation):
        return {
            "bindings": Log.bindings(output=self._stream),
            "reporters": [Log],
        }

    def progress(
        self,
        source,
        count=None,
        advance=None,
        what=None,
        total=None,
        message=None,
        parent=None,
        activity=None,
    ):
        r"""
        Write a progress update to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log(surface)
            >>> log.progress(source=surface, what='progress', count=10, total=100)
            [Ngon([1, 1, 1])] [Ngon] progress: 10/100
            >>> log.progress(source=surface, what='dimension', count=10)
            [Ngon([1, 1, 1])] [Ngon] dimension: 10/?

        """
        if advance is not None:
            return

        if count is not None and what is not None:
            line = f"{what}: {count}/{total or '?'}"
            if message:
                line = f"{line} {message}"
        elif message is not None:
            line = message
        else:
            return

        self.log(source, line)

    async def result(self, source, result, **kwargs):
        r"""
        Report a result to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> import asyncio
            >>> log = Log(surface)
            >>> result = log.result(source=surface, result="dense orbit closure", dimension=1337)
            >>> asyncio.run(result)
            [Ngon([1, 1, 1])] [Ngon] dense orbit closure (dimension: 1337)
            >>> result = log.result(source=surface, result=None)
            >>> asyncio.run(result)
            [Ngon([1, 1, 1])] [Ngon] ¯\_(ツ)_/¯

        """
        shruggie = r"¯\_(ツ)_/¯"
        result = shruggie if result is None else str(result)
        if kwargs.pop("cached", False):
            result = f"{result} (cached)"
        self.log(source, result, **kwargs)


class LogBindingSpec(BindingSpec):
    r"""
    A picklable version of a FactoryBindingSpec().

    ...
    """
    scope = "DEFAULT"
    name = "log"

    def __init__(self, output, prefix):
        self._output = output
        self._prefix = prefix

    def provide_log(self, surface):
        if self._output == "-" or (self._output is None and self._prefix is None):
            import sys
            output = sys.stdout
        elif self._output is not None:
            output = open(self._output, "w")
        elif self._prefix is not None:
            import os.path

            output = open(os.path.join(self._prefix, f"{surface.basename()}.log"), "w")

        return Log(surface, output)
