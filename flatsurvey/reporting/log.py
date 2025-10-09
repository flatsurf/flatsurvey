r"""
Writes progress and results as an unstructured log file.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "log", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker log [OPTIONS]
      Writes progress and results as an unstructured log file.
    Options:
      --output FILE       output file [default: derived automatically]
      --prefix DIRECTORY  directory for output file [default: current directory]
      --help              Show this message and exit.

::

    >>> from flatsurvey.cache.maintenance import cli as maintenance
    >>> invoke(maintenance, "log", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: cli log [OPTIONS]
      Writes progress and results as an unstructured log file.
    Options:
      --output FILE       output file [default: derived automatically]
      --prefix DIRECTORY  directory for output file [default: current directory]
      --help              Show this message and exit.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
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

from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import click

from flatsurvey.pipeline import Bindings
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class Log(Reporter, Command):
    r"""
    Writes progress and results as an unstructured log file.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon, Surface
        >>> surface = Ngon((1, 1, 1))

        >>> log = Log({Surface: surface}, output="-")
        >>> log.log(source=surface, message="Hello World")
        [Ngon([1, 1, 1])] [Ngon] Hello World

    """

    def __init__(
        self,
        configuration: dict | None = None,
        output: Path | Literal["-"] | None = None,
        prefix: Path | None = None,
    ):
        super().__init__()

        self._configuration = configuration
        self._output = output
        self._prefix = prefix

    @staticmethod
    @click.command(
        name="log",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--output",
        type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
        default=None,
        help="output file [default: derived automatically]",
    )
    @click.option(
        "--prefix",
        type=click.Path(
            exists=True,
            file_okay=False,
            dir_okay=True,
            allow_dash=False,
            path_type=Path,
        ),
        default=None,
        help="directory for output file [default: current directory]",
    )
    @Bindings.click
    def click(bindings: Bindings, output, prefix):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Log.click)

        """
        bindings.append(list[Reporter], Log)
        with bindings.scope(Log) as scoped:
            scoped.define(output=output, prefix=prefix)

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Create an instance of this class from the ``bindings`` (that have been
        typically set by :meth:`click`.)

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> bindings = Bindings()
            >>> invoke_subcommand(Log.click, bindings=bindings)
            >>> bindings.define(Surface, Ngon((1, 1, 1)))
            >>> Log.create(bindings)
            log

        """
        with bindings.scope(Log) as scoped:
            return Log(
                configuration=bindings.get("configuration", lambda: None),
                output=scoped.get("output"),
                prefix=scoped.get("prefix"),
            )

    @property
    @contextmanager
    def output(self):
        r"""
        Return a stream to write log messages to.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     log = Log({Surface: surface}, prefix=tmpdir)
            ...     with log.output as output: print(output)
            <_io.TextIOWrapper name='/.../ngon-1-1-1.txt' mode='a' encoding='UTF-8'>

        If the file already exists, then we just append to it::

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     log = Log({Surface: surface}, prefix=tmpdir)
            ...     with log.output as output: print(output)
            ...     with log.output as output: print(output)
            <_io.TextIOWrapper name='/.../ngon-1-1-1.txt' mode='a' encoding='UTF-8'>
            <_io.TextIOWrapper name='/.../ngon-1-1-1.txt' mode='a' encoding='UTF-8'>

        """
        output = self._output

        if output is None:
            dir = Path(self._prefix or Path.cwd())
            dir.mkdir(parents=True, exist_ok=True)

            prefix = "log"
            if self._configuration:
                keys = sorted(self._configuration.keys())
                prefix = "-".join(self._configuration[key].basename() for key in keys)

            suffix = ".txt"

            output = dir / f"{prefix}{suffix}"

        if output == "-":
            import sys

            yield sys.stdout
            sys.stdout.flush()
            return

        with open(output, "a") as stream:
            yield stream
            stream.flush()

    def _log(self, message):
        r"""
        Writes a ``message`` to the underlying log stream.

        TESTS::

            >>> from flatsurvey.reporting.log import Log
            >>> log = Log(output="-")
            >>> log._log("message")
            message

        """
        with self.output as output:
            output.write("%s\n" % (message,))

    def _log_prefix(self, source):
        r"""
        Return the prefix to use for each log message coming from ``source``.

        TESTS::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log({Surface: surface}, output="-")
            >>> log._log_prefix(log)
            '[Ngon([1, 1, 1])] [Log]'

        """
        prefix = f"[{type(source).__name__}]"
        if self._configuration:
            prefix = (
                " ".join(f"[{value}]" for value in self._configuration.values())
                + " "
                + prefix
            )
        return prefix

    def log(self, source, message, **kwargs):
        r"""
        Write a ``message`` to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log({Surface: surface}, output="-")
            >>> log.log(source=surface, message="Hello World", extra="data", lot="1337")
            [Ngon([1, 1, 1])] [Ngon] Hello World (extra: data) (lot: 1337)

        """
        message = f"{self._log_prefix(source)} {message}"
        for k, v in kwargs.items():
            message += f" ({k}: {v})"
        self._log(message)

    async def result(self, source, result, **kwargs):
        r"""
        Report a result to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> import asyncio
            >>> log = Log({Surface: surface}, output="-")
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

    def progress(
        self,
        source,
        count=None,
        what=None,
        total=None,
        message=None,
    ):
        r"""
        Write a progress update to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> log = Log({Surface: surface}, output="-")
            >>> log.progress(source=surface, what='progress', count=10, total=100)
            [Ngon([1, 1, 1])] [Ngon] progress: 10/100
            >>> log.progress(source=surface, what='dimension', count=10)
            [Ngon([1, 1, 1])] [Ngon] dimension: 10/?

        """
        if count is not None and what is not None:
            line = f"{what}: {count}/{total or '?'}"
            if message:
                line = f"{line} {message}"
        elif message is not None:
            line = message
        else:
            return

        self.log(source, line)


__test__ = {
    # doctests of .click do not run unless explicitly mentioned here due to the click decorator.
    "Log.click": Log.click.__doc__,
}
