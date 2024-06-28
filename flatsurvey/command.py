r"""
Utilities for subcommands that can be invoked from the command line.
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

from abc import abstractmethod


class Command:
    r"""
    A subcommand that can be invoked from the command line.

    Commands should inherit from this class.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> surface = Ngon((1, 1, 1))

        >>> from flatsurvey.reporting import Log
        >>> log = Log(surface)
        >>> isinstance(log, Command)
        True

    """

    @classmethod
    def name(cls):
        r"""
        Return the name of this command for the command line.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log.name()
            'log'

        """
        return cls.click.name

    def __repr__(self):
        r"""
        Return a printable representation of this command.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log(surface)
            >>> log
            log

        """
        return self.name()
