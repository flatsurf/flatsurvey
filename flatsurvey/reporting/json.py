r"""
Writes results to a JSON file.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "json", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker json [OPTIONS]
      Writes results in JSON format.
    Options:
      --output FILE        JSON output file [default: derived automatically]
      --prefix DIRECTORY   directory for JSON output files [default: current
                           directory]
      --pickles DIRECTORY  base directory to store pickles of non-primitive results
                           [default: pickles are not stored]
      --help               Show this message and exit.
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

from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import click

from flatsurvey.pipeline import Bindings
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class Json(Reporter, Command):
    r"""
    Writes results in JSON format.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon, Surface
        >>> surface = Ngon((1, 1, 1))
        >>> Json({Surface: surface})
        json

    """

    def __init__(
        self,
        configuration: dict | None,
        output: Path | Literal["-"] | None = None,
        prefix: Path | None = None,
        pickles: Path | None = None,
    ):
        super().__init__()

        self._configuration = configuration
        self._output = output
        self._prefix = prefix
        self._pickles = pickles

        self._data = {}
        if self._configuration:
            for key, value in self._configuration.items():
                if isinstance(key, type):
                    key = key.__name__
                key = str(key)

                # Make kebab-case (like command line commands record their configuration)
                import re

                key = re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()

                self._data.setdefault(key, value)

    @staticmethod
    @click.command(
        name="json",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--output",
        type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
        default=None,
        help="JSON output file [default: derived automatically]",
    )
    @click.option(
        "--prefix",
        type=click.Path(
            file_okay=False, dir_okay=True, allow_dash=False, path_type=Path
        ),
        default=None,
        help="directory for JSON output files [default: current directory]",
    )
    @click.option(
        "--pickles",
        type=click.Path(
            file_okay=False, dir_okay=True, allow_dash=False, path_type=Path
        ),
        default=None,
        help="base directory to store pickles of non-primitive results [default: pickles are not stored]",
    )
    @Bindings.click
    def click(bindings: Bindings, output, prefix, pickles):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Json.click)

        """
        if output is not None and prefix is not None:
            raise ValueError("at most one of output and prefix must be specified")

        bindings.append(list[Reporter], Json)
        with bindings.scope(Json) as scoped:
            scoped.define(output=output, prefix=prefix, pickles=pickles)

    @staticmethod
    def create(bindings):
        r"""
        Create a JSON reporter from the configuration in the ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> bindings = Bindings()
            >>> invoke_subcommand(Json.click, bindings=bindings)
            >>> bindings.define(Surface, Ngon((1, 1, 1)))
            >>> Json.create(bindings)
            json

        """
        with bindings.scope(Json) as scoped:
            configuration = bindings.get("configuration", lambda: None)
            output = scoped.get("output")
            prefix = scoped.get("prefix")
            pickles = scoped.get("pickles")

        return Json(
            configuration=configuration, output=output, prefix=prefix, pickles=pickles
        )

    async def result(self, source, result, **kwargs):
        r"""
        Report a ``result`` for ``source``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json({Surface: surface}, output="-")

            >>> import asyncio
            >>> asyncio.run(json.result("source", True))
            >>> json.flush()
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "source": [{"timestamp": "...", "value": true}]}

        """
        from datetime import datetime, timezone

        result = self._simplify(
            result, **{"timestamp": str(datetime.now(timezone.utc)), **kwargs}
        )

        self._data.setdefault(str(source), [])
        self._data[str(source)].append(result)

    def _serialize_to_pickle(self, obj):
        r"""
        Return a JSON serializable version of ``obj``.

        Called for objects that cannot be otherwised encoded as JSON.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     json = Json({Surface: surface}, pickles=Path(tmpdir))
            ...     json._serialize_to_pickle(True)
            {'type': 'bool', 'repr': 'True', 'pickle': '112bda3b495d867b6a98c899fac7c25eb60ca4b6e6fe5ec7ab9299f93e8274bc'}

        If no pickle directory has been configured, pickles are silently
        dropped::

            >>> json = Json({Surface: surface})
            >>> json._serialize_to_pickle(True)
            {'type': 'bool', 'repr': 'True'}

        """
        characteristics = {}

        if hasattr(obj, "_flatsurvey_characteristics"):
            characteristics = self._simplify(obj._flatsurvey_characteristics())

        characteristics.setdefault("type", type(obj).__name__)
        characteristics.setdefault("repr", repr(obj))
        if self._pickles:
            dir = self._pickles / type(obj).__name__
            dir.mkdir(parents=True, exist_ok=True)

            from flatsurvey.cache.pickles import DirectoryPickleProvider

            path, sha = DirectoryPickleProvider.dump(obj, dir)
            del path

            characteristics.setdefault("pickle", sha)

        return characteristics

    def _simplify_unknown(self, value):
        r"""
        Return the argument in a way that JSON serialization can make sense of.

        EXAMPLES:

        Anything that is unknown is rendered as its pickle, so we can let any
        object that we don't understand through without changes::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json({Surface: surface}, output="-")

            >>> import asyncio
            >>> asyncio.run(json.result("source", "verdict"))

            >>> json.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "source": [{"timestamp": "...", "value": "verdict"}]}

        """
        return value

    @property
    @contextmanager
    def output(self):
        r"""
        Return an opened file to which we write the JSON output.

        If ``output`` has not been set explicitly, the file name is
        automatically constructed so we do not overwrite existing files.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     json = Json({Surface: surface}, prefix=tmpdir)
            ...     with json.output as output: print(output)
            <_io.TextIOWrapper name='/.../ngon-1-1-1.json' mode='w' encoding='UTF-8'>

        Files get automatic numbering to not overwrite existing results::

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     json = Json({Surface: surface}, prefix=tmpdir)
            ...     with json.output as output: print(output)
            ...     with json.output as output: print(output)
            <_io.TextIOWrapper name='/.../ngon-1-1-1.json' mode='w' encoding='UTF-8'>
            <_io.TextIOWrapper name='/.../ngon-1-1-1.1.json' mode='w' encoding='UTF-8'>

        """
        output = self._output

        if output is None:
            dir = Path(self._prefix or Path.cwd())
            dir.mkdir(parents=True, exist_ok=True)

            prefix = "log"
            if self._configuration:
                keys = sorted(self._configuration.keys())
                prefix = "-".join(self._configuration[key].basename() for key in keys)

            infix = ""
            suffix = ".json"

            while (output := dir / f"{prefix}{infix}{suffix}").exists():
                if not infix:
                    infix = ".0"
                infix = f".{int(infix[1:]) + 1}"

        if output == "-":
            import sys

            yield sys.stdout
            return

        with open(output, "w") as stream:
            yield stream

    def flush(self):
        r"""
        Write reported data out as a JSON stream.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json({Surface: surface}, output="-")

            >>> import asyncio
            >>> asyncio.run(json.result("source", "verdict"))

        Note that each result is reported individually, so the "verdict" is a list here::

            >>> json.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}, "source": [{"timestamp": "...", "value": "verdict"}]}

        """
        import json
        import sys

        with self.output as output:
            output.write(json.dumps(self._data, default=self._serialize_to_pickle))
            output.flush()


__test__ = {
    # doctests of Json.click do not run unless explicitly mentioned here due to the click decorator.
    "Json.click": Json.click.__doc__,
}
