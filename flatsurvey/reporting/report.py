r"""
Wraps several reporters to report on progress and results.

EXAMPLES::

    >>> from flatsurvey.surfaces import Ngon
    >>> surface = Ngon((1, 1, 1))

    >>> from flatsurvey.reporting import Log
    >>> log = Log(surface)
    >>> report = Report([log])
    >>> report.log(surface, "Hello World")
    [Ngon((1, 1, 1))] [Ngon] Hello World

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

class Report:
    r"""
    A simple wrapper of several ``reporters`` that dispatches reporting.

    EXAMPLES::

        >>> report = Report([])
        >>> report.log(report, "invisible message because no reporter has been registered")

    """
    def __init__(self, reporters):
        self._reporters = reporters

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
            [Ngon((1, 1, 1))] [Ngon] Hello World printed by two identical reporters
            [Ngon((1, 1, 1))] [Ngon] Hello World printed by two identical reporters

        """
        for reporter in self._reporters:
            reporter.log(source, message, **kwargs)

    def result(self, source, result, **kwargs):
        r"""
        Report a final ``result`` of a computation from ``source``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> report = Report([log, log])
            >>> report.result(surface, "Computation completed.")
            [Ngon((1, 1, 1))] [Ngon] Computation completed.
            [Ngon((1, 1, 1))] [Ngon] Computation completed.

        """
        for reporter in self._reporters:
            reporter.result(source, result, **kwargs)

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
            [Ngon((1, 1, 1))] [Ngon] dimension: 13/37
            [Ngon((1, 1, 1))] [Ngon] dimension: 13/37

        """
        for reporter in self._reporters:
            reporter.progress(source, unit, count, total)
