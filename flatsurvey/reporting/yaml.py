r"""
Writes computation results as YAML files.

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
#        Copyright (C) 2020-2022 Julian Rüth
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

from flatsurvey.reporting.reporter import Reporter
from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


class Yaml(Reporter, Command):
    r"""
    Writes results to a YAML file.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))
        >>> log = Yaml(surface)

        >>> import asyncio
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
        >>> from flatsurvey.reporting import Report
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=None, saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))
        >>> ccp = CompletelyCylinderPeriodic(report=Report([log]), flow_decompositions=flow_decompositions, cache=None)
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
        super().__init__()

        self._data = {"surface": surface}

        import sys
        self._stream = stream or sys.stdout

        from ruamel.yaml import YAML

        self._yaml = YAML()
        self._yaml.width = 2**16
        self._yaml.representer.default_flow_style = None
        self._yaml.representer.add_representer(type(None), Yaml._represent_as_null)
        self._yaml.representer.add_representer(None, Yaml._represent_as_pickle)
        self._yaml.register_class(type(self._data["surface"]))
        self._yaml.register_class(Yaml.Pickle)

    @classmethod
    def _represent_as_null(cls, representer, data):
        r"""
        Return a YAML serialization as ``null``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        This is registered for ``None``::

            >>> log = Yaml(surface)

            >>> log._data["result"] = log._simplify(None)

            >>> log.flush()
            surface:
            ...
            result:

        """
        return representer.represent_scalar('tag:yaml.org,2002:null', '')

    @classmethod
    def _represent_as_pickle(cls, representer, data):
        r"""
        Return a YAML serialization by serializing to a pickle.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

        This is registered for any type that does not implement YAML serialization::

            >>> log = Yaml(surface)

            >>> log._data["result"] = log._simplify(log)

            >>> log.flush()
            surface:
            ...
            result: {pickle: !!binary ...

        """
        import pickle

        return representer.represent_data(
            {
                "pickle": Yaml.Pickle(pickle.dumps(data)),
            }
        )

    async def result(self, source, result, **kwargs):
        r"""
        Report that computation ``source`` concluded with ``result``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> log = Yaml(surface)

            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections, CompletelyCylinderPeriodic
            >>> from flatsurvey.reporting import Report
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([log]), saddle_connection_orientations=SaddleConnectionOrientations(SaddleConnections(surface, report=None), report=None))

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
        self._data[str(source)].append(self._simplify(result, **kwargs))

    def _simplify_unknown(self, value):
        r"""
        Return the argument in a way that YAML serialization can make sense of.

        EXAMPLES:

        Anything that is unknown is rendered as its pickle, so we can let any
        object that we don't understand through without changes::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))
            >>> log = Yaml(surface)

            >>> import asyncio
            >>> asyncio.run(log.result("verdict", result=asyncio))

            >>> log.flush()
            surface:
            ...
            verdict:
            - {pickle: !!binary "gASVNgAAAAAAAACMEXNhZ2UubWlzYy5mcGlja2xllIwOdW5waWNrbGVNb2R1bGWUk5SMB2FzeW5j\naW+UhZRSlC4=\n"}

        """
        if hasattr(type(value), "to_yaml"):
            self._yaml.representer.add_representer(type(value), type(value).to_yaml)
            return value

        return value

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

    class Pickle:
        r"""
        Wrapper for objects that should be stored as their pickles in the YAML output.
        """
        @copy_args_to_internal_fields
        def __init__(self, raw):
            pass

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
