r"""
Abstract interface to report progress and results of computations.

EXAMPLES::

    >>> from flatsurvey.reporting import Log
    >>> Reporter in Log.mro()
    True

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

class Reporter:
    r"""
    Base class for something that can log progress and results of computations.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> from flatsurvey.reporting import Log
        >>> log = Log(surface)
        >>> isinstance(log, Reporter)
        True

    """
    def log(self, source, message, **kwargs):
        r"""
        Write ``message`` emitted by ``source`` to this log.

        Most implementations will not implement this and simply ignore such messages.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.log(source=surface, message="Hello World", additional_data=1337)
            [Ngon((1, 1, 1))] [Ngon] Hello World (additional_data: 1337)

        """
        pass

    def result(self, source, result, **kwargs):
        r"""
        Report a computation's ``result`` from ``source``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.result(source=surface, result="result", additional_data=1337)
            [Ngon((1, 1, 1))] [Ngon] result (additional_data: 1337)

        """
        pass

    def progress(self, source, unit, count, total=None):
        r"""
        Report that ``source`` has made some progress.

        Most implementations will not implement this and simply ignore such messages.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.progress(source=surface, unit="progress", count=13, total=37)
            [Ngon((1, 1, 1))] [Ngon] progress: 13/37

        """
        pass

    def flush(self):
        r"""
        Make sure that any output has been flushed.

        Most implementation will not need to implement this.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.flush()

        """
        pass

    def command(self):
        r"""
        Return the command that can be used to configure this reporter with the
        arguments that provide it in its current configuration.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.command()
            ['log']

        """
        raise NotImplementedError

    def __repr__(self):
        return " ".join(self.command())

