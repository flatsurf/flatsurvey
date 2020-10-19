r"""
The saddle connections on a translation surface.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "saddle-connection-orientations", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker saddle-connection-orientations [OPTIONS]
      Orientations of saddle connections on the surface, i.e., the vectors of
      saddle connections irrespective of scaling and sign.
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


class SaddleConnectionOrientations(Processor):
    r"""
    Orientations of saddle connections on the surface, i.e., the vectors of
    saddle connections irrespective of scaling and sign.
    """
    @copy_args_to_internal_fields
    def __init__(self, saddle_connections):
        super().__init__(producers=[saddle_connections])
        self._seen = None

    def _consume(self, connection, cost):
        vector = connection.vector()
        if self._seen == None:
            import cppyy
            self._seen = cppyy.gbl.std.set[type(vector), type(vector).CompareSlope]()

        if vector.x():
            try:
                vector = type(vector)(vector.x() / vector.x(), vector.y() / vector.x())
            except Exception: pass
        if vector.y():
            try:
                vector = type(vector)(vector.x() / vector.y(), vector.y() / vector.y())
            except Exception: pass


        import cppyy
        flat_triangulation = self._saddle_connections._surface.flat_triangulation()
        source = cppyy.gbl.flatsurf.Vertex.source(connection.source(), flat_triangulation.combinatorial())
        target = cppyy.gbl.flatsurf.Vertex.source(connection.target(), flat_triangulation.combinatorial())
        if self._seen.find(vector) == self._seen.end():
            self._seen.insert(vector)
            self._current = connection.vector()
            self._notify_consumers(cost)

        return not Processor.COMPLETED

    @classmethod
    @click.command(name="saddle-connection-orientations", cls=GroupedCommand, group="Intermediates", help=__doc__.split('EXAMPLES')[0])
    def click():
        return {
            'bindings': SaddleConnectionOrientations
        }

    def command(self):
        return ["saddle-connection-orientations"]
