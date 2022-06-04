# TODO: Implement me.
r"""
Writes results as machine readable JSON files.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "json", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker json [OPTIONS]
      Writes results as machine readable JSON files.
    Options:
      --output FILENAME  [default: derived from surface name]
      --help             Show this message and exit.

"""

import click

from flatsurvey.pipeline.util import FactoryBindingSpec
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui.group import GroupedCommand


# TODO: Should we just parse & dump the YAML?
class Json(Reporter):
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

    pass
