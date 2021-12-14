r"""
Writes computation results as machine readable YAML files.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "yaml", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker yaml [OPTIONS]
      Writes results to a YAML file.
    Options:
      --output FILENAME  [default: derived from surface name]
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
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui.group import GroupedCommand


class Pickle:
    def __init__(self, raw):
        self._raw = raw

    @classmethod
    def to_yaml(cls, representer, data):
        import base64

        return representer.represent_scalar(
            "tag:yaml.org,2002:binary",
            base64.encodebytes(data._raw).decode("ascii"),
            style="",
        )

    @classmethod
    def from_yaml(self, constructor, obj):
        raise NotImplementedError


class Yaml(Reporter):
    r"""
    Writes results to a YAML file.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))
        >>> log = Yaml(surface)

        >>> import asyncio
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
        >>> from flatsurvey.reporting import Report
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))
        >>> ccp = CompletelyCylinderPeriodic(report=Report([log]), flow_decompositions=flow_decompositions)
        >>> report = ccp.report()
        >>> asyncio.run(report)

        >>> log.flush() # doctest: +ELLIPSIS
        surface:
        ...
        completely-cylinder-periodic:
        - {cylinder_periodic_directions: 0, undetermined_directions: 0, value: null}

    """

    @copy_args_to_internal_fields
    def __init__(self, surface, stream=None):
        import sys

        self._stream = stream or sys.stdout

        self._data = {"surface": surface}

        from ruamel.yaml import YAML

        self._yaml = YAML()
        self._yaml.width = 2 ** 16
        self._yaml.representer.default_flow_style = None
        self._yaml.representer.add_representer(None, Yaml._represent_undefined)
        self._yaml.register_class(type(self._data["surface"]))
        self._yaml.register_class(Pickle)

    @classmethod
    def _represent_undefined(cls, representer, data):
        import pickle

        return representer.represent_data(
            {
                "pickle": Pickle(pickle.dumps(data)),
                "repr": repr(data),
            }
        )

    def _render(self, *args, **kwargs):
        if len(args) == 0:
            return self._render(kwargs)

        if len(args) > 1:
            return self._render(args, **kwargs)

        value = args[0]
        if not kwargs:
            from sage.all import ZZ

            if type(value) is type(ZZ()):
                value = int(value)
            if hasattr(type(value), "to_yaml"):
                self._yaml.representer.add_representer(type(value), type(value).to_yaml)
            return value

        value = self._render(value)
        ret = self._render(kwargs)
        if isinstance(value, dict):
            ret.update(value)
        else:
            ret["value"] = value

            from pickle import dumps

            try:
                dumps(value)
            except Exception as e:
                ret["value"] = "Failed: " + str(e)
        return ret

    async def result(self, source, result, **kwargs):
        r"""
        Report that computation ``source`` concluded with ``result``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> log = Yaml(surface)

            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
            >>> from flatsurvey.reporting import Report
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([log]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface)))

        Write the first two flow decompositions to the YAML output:

            >>> import asyncio
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            True
            >>> produce = flow_decompositions.produce()
            >>> asyncio.run(produce)
            True

            >>> log.flush() # doctest: +ELLIPSIS
            surface:
            ...
            flow-decompositions:
            - orientation: ...
            - orientation: ...

        """
        self._data.setdefault(str(source), [])
        self._data[str(source)].append(self._render(result, **kwargs))

    def flush(self):
        r"""
        Write out the full YAML document.

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> log = Yaml(surface)
            >>> log.flush() # doctest: +ELLIPSIS
            surface:
            ...

        """
        self._yaml.dump(self._data, self._stream)
        self._stream.flush()

    @classmethod
    @click.command(
        name="yaml",
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
                    "yaml",
                    lambda surface: Yaml(
                        surface,
                        stream=output or open(f"{surface.basename()}.yaml", "w"),
                    ),
                )
            ],
            "reporters": [Yaml],
        }

    def command(self):
        import sys

        command = ["yaml"]
        if self._stream is not sys.stdout:
            command.append(f"--output={self._stream.name}")
        return command
