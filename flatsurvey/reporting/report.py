r"""
Wraps several reporters to report on progress and results.

EXAMPLES::

    >>> from flatsurvey.surfaces import Ngon
    >>> surface = Ngon((1, 1, 1))

    >>> from flatsurvey.reporting import Log
    >>> log = Log(surface)
    >>> report = Report([log])
    >>> report.log(surface, "Hello World")
    [Ngon([1, 1, 1])] [Ngon] Hello World

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

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


class Report(Command):
    r"""
    Generic reporting of results.

    A simple wrapper of several ``reporters`` that dispatches reporting.

    EXAMPLES::

        >>> report = Report([])
        >>> report.log(report, "invisible message because no reporter has been registered")

    """

    def __init__(self, reporters, ignore=None):
        self._reporters = reporters
        self._ignore = ignore or []

    @classmethod
    @click.command(
        name="report",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES:")[0],
    )
    @click.option("--ignore", type=str, multiple=True)
    def click(ignore):
        return {"bindings": [PartialBindingSpec(Report)(ignore=ignore)]}

    def log(self, source, message, **kwargs):
        r"""
        Write an informational message to the log.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
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

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> import asyncio
            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
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

    def progress(self, source, unit, count, total=None):
        r"""
        Report that some progress has been made in the resolution of the
        computation ``source``. Now we are at ``count`` of ``total`` given in
        multiples of ``unit``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> report = Report([log, log])
            >>> report.progress(surface, unit="dimension", count=13, total=37)
            [Ngon([1, 1, 1])] [Ngon] dimension: 13/37
            [Ngon([1, 1, 1])] [Ngon] dimension: 13/37

        """
        if self.ignore(source):
            return
        for reporter in self._reporters:
            reporter.progress(source, unit, count, total)

    def ignore(self, source):
        if type(source).__name__ in self._ignore:
            return True
        if isinstance(source, Command) and source.name() in self._ignore:
            return True

        return False

    def command(self):
        return ["report"] + [f"--ignore={i}" for i in self._ignore]

    def deform(self, deformation):
        return {"bindings": [PartialBindingSpec(Report)(ignore=self._ignore)]}

    def flush(self):
        for reporter in self._reporters:
            reporter.flush()
