r"""
Wraps several reporters to report on progress and results.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "report", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker report [OPTIONS]
      Generic reporting of results.
      A simple wrapper of several ``reporters`` that dispatches reporting.
    Options:
      --ignore TEXT  [default: flow-decompositions, saddle-connections, saddle-
                     connection-orientations]
      --help         Show this message and exit.

::

    >>> from flatsurvey.surfaces import Ngon, Surface
    >>> surface = Ngon((1, 1, 1))

    >>> from flatsurvey.reporting import Log
    >>> log = Log({Surface: surface}, output="-")
    >>> report = Report([log])
    >>> report.log(surface, "Hello World")
    [Ngon([1, 1, 1])] [Ngon] Hello World

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

from typing import List

import click

from flatsurvey.pipeline import Bindings
from flatsurvey.reporting.reporter import Reporter
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class Report(Command):
    r"""
    Generic reporting of results.

    A simple wrapper of several ``reporters`` that dispatches reporting.

    EXAMPLES::

        >>> report = Report([])
        >>> report.log(report, "invisible message because no reporter has been registered")

    """

    DEFAULT_IGNORE = [
        "flow-decompositions",
        "saddle-connections",
        "saddle-connection-orientations",
    ]

    def __init__(
        self, reporters: List[Reporter] | None = None, ignore: list[str] | None = None
    ):
        if reporters is None:
            reporters = []
        if ignore is None:
            ignore = Report.DEFAULT_IGNORE

        self._reporters = reporters
        self._ignore = ignore

        # Keep track which goals have already reported their result (this is a
        # bit of a hack…)
        from flatsurvey.pipeline import Consumer

        self._reported: set[Consumer] = set()

    @staticmethod
    @click.command(
        name="report",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES:")[0],  # type: ignore
    )
    @click.option(
        "--ignore", type=str, multiple=True, default=DEFAULT_IGNORE, show_default=True
    )
    @Bindings.click
    def click(bindings: Bindings, ignore):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Report.click)

        """
        with bindings.scope(Report) as scoped:
            scoped.define(ignore=ignore)

    @staticmethod
    def create(bindings):
        r"""
        Create a report from the configuration in the ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> bindings = Bindings()
            >>> invoke_subcommand(Report.click, bindings=bindings)
            >>> bindings.define(Surface, Ngon((1, 1, 1)))
            >>> report = Report.create(bindings)

            >>> report._ignore
            ('flow-decompositions', 'saddle-connections', 'saddle-connection-orientations')

        Note that we do not set a default reporter to stdout. If no reporter is
        specified, then no reporting at all is going to happen::

            >>> report._reporters
            []

        """
        with bindings.scope(Report) as scoped:
            reporters = bindings.get(list[Reporter], default=lambda: [])
            ignore = scoped.get("ignore", default=Report.DEFAULT_IGNORE)

            return Report(reporters=reporters, ignore=ignore)

    def log(self, source, message, **kwargs):
        r"""
        Write an informational message to the report.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> report = Report([log, log])
            >>> report.log(surface, "Hello World printed by two identical reporters")
            [Ngon([1, 1, 1])] [Ngon] Hello World printed by two identical reporters
            [Ngon([1, 1, 1])] [Ngon] Hello World printed by two identical reporters

        """
        if self.ignore(source):
            return

        for reporter in self._reporters:
            reporter.log(source, message, **kwargs)

    async def result(self, source, result, **kwargs):
        r"""
        Report a final ``result`` of a computation from ``source``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> _ = surface.polygon()  # called to make hashing work below

            >>> import asyncio
            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> report = Report([log, log])
            >>> result = report.result(surface, "Computation completed.")
            >>> asyncio.run(result)
            [Ngon([1, 1, 1])] [Ngon] Computation completed.
            [Ngon([1, 1, 1])] [Ngon] Computation completed.

        """
        if self.ignore(source):
            return

        for reporter in self._reporters:
            await reporter.result(source, result, **kwargs)

        self._reported.add(source)

    def progress(
        self,
        source,
        count=None,
        what=None,
        total=None,
        message=None,
    ):
        r"""
        Report that some progress has been made in the resolution of the
        computation ``source``. Now we are at ``count`` of ``total`` given as
        ``what``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> report = Report([log, log])
            >>> context = report.progress(surface, what="dimension", count=13, total=37)
            [Ngon([1, 1, 1])] [Ngon] dimension: 13/37
            [Ngon([1, 1, 1])] [Ngon] dimension: 13/37

        """
        if self.ignore(source):
            return

        for reporter in self._reporters:
            reporter.progress(
                source=source,
                what=what,
                count=count,
                total=total,
                message=message,
            )

    def ignore(self, source) -> bool:
        r"""
        Return whether data from ``source`` should be ignored by this report.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> from flatsurvey.jobs import FlowDecompositions, OrbitClosure
            >>> bindings = Bindings()
            >>> surface = Ngon((1, 1, 1))
            >>> invoke_subcommand(Report.click, bindings=bindings)
            >>> bindings.define(Surface, surface)
            >>> report = Report.create(bindings)

            >>> report.ignore(surface)
            False

            >>> flow_decompositions = bindings.get(FlowDecompositions)
            >>> report.ignore(flow_decompositions)
            True

            >>> orbit_closure = bindings.get(OrbitClosure)
            >>> report.ignore(orbit_closure)
            False

        """
        if type(source).__name__ in self._ignore:
            return True
        if isinstance(source, Command) and source.name() in self._ignore:
            return True

        return False

    def flush(self):
        r"""
        Ensure that all reported data has been written out.

        EXAMPLES::

            >>> from flatsurvey.reporting import Json, Report
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> json = Json({Surface: surface}, output="-")
            >>> report = Report([json])

            >>> report.flush()
            {"surface": {"angles": [1, 1, 1], "genus": 1, "type": "Ngon", "repr": "Ngon([1, 1, 1])"}}

        """
        for reporter in self._reporters:
            reporter.flush()


__test__ = {
    # doctests of .click do not run unless explicitly mentioned here due to the click decorator.
    "Report.click": Report.click.__doc__,
}
