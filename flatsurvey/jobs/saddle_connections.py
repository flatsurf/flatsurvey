r"""
The saddle connections on a translation surface.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "saddle-connections", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker saddle-connections [OPTIONS]
      Saddle connections on the surface.
    Options:
      --help  Show this message and exit.

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

import click

from pinject import copy_args_to_internal_fields

from flatsurvey.ui.group import GroupedCommand
from flatsurvey.pipeline import Producer, Processor
from flatsurvey.pipeline.util import PartialBindingSpec

class SaddleConnections(Producer):
    r"""
    Saddle connections on the surface.
    """
    DEFAULT_BOUND = None
    DEFAULT_LIMIT = None

    @copy_args_to_internal_fields
    def __init__(self, surface, limit=DEFAULT_LIMIT, bound=DEFAULT_BOUND):
        super().__init__()

        self._connections = None

    def _by_length(self):
        self.__connections = self._surface.orbit_closure()._surface.connections().byLength()
        if self._bound is not None:
            self.__connections = self.__connections.bound(self._bound)
        if self._limit is not None:
            from itertools import islice
            self.__connections = islice(self.__connections, 0, self._limit)
        self._connections = iter(self.__connections)

    def randomize(self, lower_bound):
        self.__connections = self._surface.orbit_closure()._surface.connections().sample().lowerBound(lower_bound)
        if self._bound is not None:
            raise NotImplementedError("Cannot randomize saddle connections with --bound yet.")
        if self._limit is not None:
            from itertools import islice
            self.__connections = islice(self.__connections, 0, self._limit)
        self._connections = iter(self.__connections)

    def _produce(self):
        if self._connections is None:
            self._by_length()
        try:
            self._current = next(self._connections)
            return not Producer.EXHAUSTED
        except StopIteration:
            return Producer.EXHAUSTED

    @classmethod
    @click.command(name="saddle-connections", cls=GroupedCommand, group="Intermediates", help=__doc__.split('EXAMPLES')[0])
    @click.option("--bound", type=int, default=DEFAULT_BOUND, help="stop search after all saddle connections up to that length have been processed  [default: no bound]")
    @click.option("--limit", type=int, default=DEFAULT_LIMIT, help="stop search after that many saddle connections have been considered  [default: no limit]")
    def click(bound, limit):
        return {
            'bindings': [ PartialBindingSpec(SaddleConnections)(bound=bound, limit=limit) ]
        }

    def command(self):
        command = ["saddle-connections"]
        if self._bound != self.DEFAULT_BOUND:
            command.append(f"--bound={self._bound}")
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        return command
