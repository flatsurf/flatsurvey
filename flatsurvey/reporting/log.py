r"""
Writes progress and results as an unstructured log file.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "log", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker log [OPTIONS]
      Writes progress and results as an unstructured log file.
    Options:
      --output FILENAME  [default: stdout]
      --help             Show this message and exit.

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click

from pinject import copy_args_to_internal_fields

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.pipeline.util import FactoryBindingSpec

class Log(Reporter):
    r"""
    Writes progress and results as an unstructured log file.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> log = Log(surface)
        >>> log.log(source=surface, message="Hello World")
        [Ngon((1, 1, 1))] [Ngon] Hello World

    """
    @copy_args_to_internal_fields
    def __init__(self, surface, stream=None):
        import sys
        self._stream = stream or sys.stdout

    def _prefix(self, source):
        return f"[{self._surface}] [{type(source).__name__}]"

    def _log(self, message):
        self._stream.write("%s\n"%(message,))
        self._stream.flush()

    def log(self, source, message, **kwargs):
        r"""
        Write a ``message`` to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log(surface)
            >>> log.log(source=surface, message="Hello World", extra="data", lot="1337")
            [Ngon((1, 1, 1))] [Ngon] Hello World (extra: data) (lot: 1337)

        """
        message = f"{self._prefix(source)} {message}"
        for k,v in kwargs.items():
            message += f" ({k}: {v})"
        self._log(message)

    @classmethod
    @click.command(name="log", cls=GroupedCommand, group="Reports", help=__doc__.split('EXAMPLES')[0])
    @click.option("--output", type=click.File("w"), default=None, help="[default: stdout]")
    def click(output):
        return {
            "bindings": [ FactoryBindingSpec("log", lambda surface: Log(surface, output or open(f"{surface}.log", "w"))) ],
            "reporters": [ Log ],
        }

    def progress(self, source, unit, count, total=None):
        r"""
        Write a progress update to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log(surface)
            >>> log.progress(source=surface, unit='progress', count=10, total=100)
            [Ngon((1, 1, 1))] [Ngon] progress: 10/100
            >>> log.progress(source=surface, unit='dimension', count=10)
            [Ngon((1, 1, 1))] [Ngon] dimension: 10/?

        """
        self.log(source, f"{unit}: {count}/{total or '?'}")

    def result(self, source, result, **kwargs):
        r"""
        Report a result to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log(surface)
            >>> log.result(source=surface, result="dense orbit closure", dimension=1337)
            [Ngon((1, 1, 1))] [Ngon] dense orbit closure (dimension: 1337)
            >>> log.result(source=surface, result=None)
            [Ngon((1, 1, 1))] [Ngon] ¯\_(ツ)_/¯

        """
        shruggie = r'¯\_(ツ)_/¯'
        self.log(source, shruggie if result is None else result, **kwargs)

    def command(self):
        command = ["log"]
        import sys
        if self._stream is not sys.stdout:
            command.append(f"--output={self._stream.name}")
        return command
