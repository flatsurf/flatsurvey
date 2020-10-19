r"""
Computes the GL₂(R) orbit closure of a surface.

Naturally, this will only find a lower bound for the orbit closure, i.e., the
space it finds might be too small because not enough directions have been
investigated that would lead us to the full space.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "orbit-closure", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker orbit-closure [OPTIONS]
      Determine the GL₂(R) orbit closure of ``surface``.
    Options:
      --limit INTEGER       abort search after processing that many flow
                            decompositions with cylinders without an increase in
                            dimension  [default: 64]
      --expansions INTEGER  when the --limit has been reached, restart the search
                            with random saddle connections that are twice as long as
                            the ones used previously; repeat this doubling process
                            EXPANSIONS many times  [default: 6]
      --help                Show this message and exit.

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

from sage.all import cached_method

from flatsurvey.jobs.flow_decomposition import FlowDecompositions
from flatsurvey.pipeline import Consumer
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.pipeline.util import PartialBindingSpec

class OrbitClosure(Consumer):
    r"""
    Determine the GL₂(R) orbit closure of ``surface``.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
        >>> OrbitClosure(surface=surface, report=Report([]), flow_decompositions=flow_decompositions, saddle_connections=connections)
        orbit-closure

    """
    DEFAULT_LIMIT = 64
    DEFAULT_EXPANSIONS = 6

    @copy_args_to_internal_fields
    def __init__(self, surface, report, flow_decompositions, saddle_connections, limit=DEFAULT_LIMIT, expansions=DEFAULT_EXPANSIONS):
        super().__init__(producers=[flow_decompositions])

        self._cylinders_without_increase = 0
        self._directions_with_cylinders = 0
        self._directions = 0
        self._expansions_performed = 0

    @classmethod
    @click.command(name="orbit-closure", cls=GroupedCommand, group="Goals", help=__doc__.split('EXAMPLES')[0])
    @click.option("--limit", type=int, default=DEFAULT_LIMIT, show_default=True, help="abort search after processing that many flow decompositions with cylinders without an increase in dimension")
    @click.option("--expansions", type=int, default=DEFAULT_EXPANSIONS, show_default=True, help="when the --limit has been reached, restart the search with random saddle connections that are twice as long as the ones used previously; repeat this doubling process EXPANSIONS many times")
    def click(limit, expansions):
        return {
            "goals": [OrbitClosure],
            "bindings": [PartialBindingSpec(OrbitClosure)(limit=limit, expansions=expansions)],
        }

    def command(self):
        command = ["orbit-closure"]
        if self._limit != self.DEFAULT_LIMIT:
            command.append(f"--limit={self._limit}")
        if self._expansions != self.DEFAULT_EXPANSIONS:
            command.append(f"--expansions={self._expansions}")
        return command

    def _consume(self, decomposition, cost):
        r"""
        Enlarge the orbit closure from the cylinders in ``decomposition``.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon
            >>> from flatsurvey.reporting import Log, Report
            >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
            >>> surface = Ngon((1, 3, 5))
            >>> connections = SaddleConnections(surface)
            >>> log = Log(surface=surface)
            >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
            >>> oc = OrbitClosure(surface=surface, report=Report([log]), flow_decompositions=flow_decompositions, saddle_connections=connections)
        
        Run until we find the orbit closure, i.e., investigate in two directions::

            >>> assert oc.resolve() == Consumer.COMPLETED
            [Ngon((1, 3, 5))] [OrbitClosure] dimension: 4/6
            [Ngon((1, 3, 5))] [OrbitClosure] dimension: 6/6
            [Ngon((1, 3, 5))] [OrbitClosure] GL(2,R)-orbit closure of dimension at least 6 in H_3(4) (ambient dimension 6) (dimension: 6) (directions: 2) (directions_with_cylinders: 2) (dense: True)

        """
        self._directions += 1

        if decomposition.decomposition.cylinders() and not decomposition.decomposition.undeterminedComponents():
            self._cylinders_without_increase += 1
            self._directions_with_cylinders += 1

        orbit_closure = self._surface.orbit_closure()
        dimension = orbit_closure.dimension()

        orbit_closure.update_tangent_space_from_flow_decomposition(decomposition)

        self._report.progress(self, "dimension", orbit_closure.dimension(), self._surface.orbit_closure_dimension_upper_bound)

        assert orbit_closure.dimension() <= self._surface.orbit_closure_dimension_upper_bound, "%s <= %s"%(orbit_closure.dimension(), self._surface.orbit_closure_dimension_upper_bound)

        if dimension != orbit_closure.dimension():
            self._cylinders_without_increase = 0

        if orbit_closure.dimension() == self._surface.orbit_closure_dimension_upper_bound:
            self.report()
            return Consumer.COMPLETED

        if self._cylinders_without_increase >= self._limit:
            if self._expansions_performed < self._expansions:
                import pyflatsurf

                self._expansions_performed += 1

                longest = self._saddle_connections._current.vector()
                lower_bound = pyflatsurf.flatsurf.Bound.upper(longest)
                lower_bound *= 2

                self._report.log(self, f"Found too many cylinders without improvements. Now considering directions coming from saddle connections of length more than {lower_bound}")
                self._saddle_connections.randomize(lower_bound)
                self._cylinders_without_increase = 0
                return not Consumer.COMPLETED

            self.report()
            return Consumer.COMPLETED

        return not Consumer.COMPLETED

    def report(self):
        if self._resolved != Consumer.COMPLETED:
            orbit_closure = self._surface.orbit_closure()
            self._report.result(self, orbit_closure, dimension=orbit_closure.dimension(), directions=self._directions, directions_with_cylinders=self._directions_with_cylinders, dense=orbit_closure.dimension() == self._surface.orbit_closure_dimension_upper_bound or None)


