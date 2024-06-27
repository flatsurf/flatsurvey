r"""
Writes results as JSON files.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.worker import worker
    >>> invoke(worker, "json", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker json [OPTIONS]
      Writes results in JSON format.
    Options:
      --output FILENAME  [default: derived from surface name]
      --help             Show this message and exit.

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
from pinject import copy_args_to_internal_fields

from flatsurvey.command import Command
from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui.group import GroupedCommand


class Json(Reporter, Command):
    r"""
    Writes results in JSON format.

    EXAMPLES::

        >>> from flatsurvey.reporting.json import Json
        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))
        >>> Json(surface)
        json

    """

    @copy_args_to_internal_fields
    def __init__(self, surface, stream=None):
        super().__init__()

        import sys

        self._stream = stream or sys.stdout

        self._data = {"surface": surface}

    @classmethod
    @click.command(
        name="json",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--output",
        type=click.File("w"),
        default=None,
        help="[default: derived from surface name]",
    )
    def click(output):
        return {
            "bindings": [
                FactoryBindingSpec(
                    "json",
                    lambda surface: Json(
                        surface,
                        stream=output or open(f"{surface.basename()}.json", "w"),
                    ),
                )
            ],
            "reporters": [Json],
        }

    async def result(self, source, result, **kwargs):
        r"""
        Report a ``result`` for ``source``.

        EXAMPLES::

            >>> from flatsurvey.reporting.json import Json
            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json(surface)

            >>> import asyncio
            >>> asyncio.run(json.result(source=None, result=True))

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

            >>> from flatsurvey.reporting.json import Json
            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json(surface)

            >>> json._serialize_to_pickle(True)
            {'type': 'bool', 'pickle': 'gASILg=='}

        """
        import base64
        from pickle import dumps

        characteristics = {}

        if hasattr(obj, "_flatsurvey_characteristics"):
            characteristics = obj._flatsurvey_characteristics()

        characteristics.setdefault("type", type(obj).__name__)
        characteristics.setdefault(
            "pickle", base64.encodebytes(dumps(obj)).decode("utf-8").strip()
        )

        return characteristics

    def _simplify_unknown(self, value):
        r"""
        Return the argument in a way that JSON serialization can make sense of.

        EXAMPLES:

        Anything that is unknown is rendered as its pickle, so we can let any
        object that we don't understand through without changes::

            >>> from flatsurvey.reporting.json import Json
            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json(surface)

            >>> import asyncio
            >>> asyncio.run(json.result("verdict", result=asyncio))

            >>> json.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "verdict": [{"timestamp": ..., "value": {"type": "module", "pickle": "..."}}]}

        """
        return value

    def flush(self):
        r"""
        Write reported data out as a JSON stream.

        EXAMPLES::

            >>> from flatsurvey.reporting.json import Json
            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json(surface)

            >>> import asyncio
            >>> asyncio.run(json.result("verdict", result=True))

        Note that each result is reported individually, so the "verdict" is a list here::

            >>> json.flush()  # doctest: +ELLIPSIS
            {"surface": {"angles": [1, 1, 1], "type": "Ngon", "pickle": "..."}, "verdict": [{"timestamp": ..., "value": true}]}

        """
        import json

        self._stream.write(json.dumps(self._data, default=self._serialize_to_pickle))
        self._stream.flush()
