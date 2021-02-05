r"""
Track Interval Exchange Transformations that cannot be decided.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "undetermined-iet", "--help") # doctest: +NORMALIZE_WHITESPACE
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
#        Copyright (C) 2021 Julian Rüth
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

import pyintervalxt
import pyexactreal
import pyeantic
import cppyy
# TODO: Make this iet serializable in pyintervalxt by simply saying dumps(iet.forget())
# i.e., when serializing an IET of unknown type (as is this one because
# (a) it comes from C++ and was not constructed in Python and (b) it
# has intervalxt::sample::Lengths and not intervalxt::cppyy::Lengths)
# be smart about registering the right types in cppyy. (If possible.)
# TODO: Expose something like this construction() in intervalxt.
cppyy.cppdef(r'''
#include <boost/type_erasure/any_cast.hpp>

template <typename T> std::tuple<std::vector<eantic::renf_elem_class>, std::vector<int> > construction(T& iet) {
    std::vector<eantic::renf_elem_class> lengths;
    std::vector<int> permutation;
    const auto bottom = iet.bottom();
    for (auto& label : iet.top()) {
        lengths.push_back(boost::type_erasure::any_cast<eantic::renf_elem_class>(iet.lengths()->forget().get(label)));
        permutation.push_back(std::find(std::begin(bottom), std::end(bottom), label) - std::begin(bottom));
    }

    return std::make_tuple(lengths, permutation);
}
''')

class UndeterminedIntervalExchangeTransformation(Consumer):
    r"""
    Track undetermined Interval Exchang Transformations.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> from flatsurvey.cache import Cache
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
        >>> UndeterminedIntervalExchangeTransformation(surface=surface, report=Report([]), flow_decompositions=flow_decompositions, saddle_connections=connections, cache=Cache())
        undetermined-iet

    """
    @copy_args_to_internal_fields
    def __init__(self, surface, report, flow_decompositions, saddle_connections, cache):
        super().__init__(producers=[flow_decompositions])

    # def resolve(self):
    #     r"""
    #     This job can never resolve, so return immediately but
    #     never mark it as resolved.

    #     EXAMPLES::

    #         >>> TODO

    #     """
    #     return not Consumer.COMPLETED

    @classmethod
    @click.command(name="undetermined-iet", cls=GroupedCommand, group="Goals", help=__doc__.split('EXAMPLES')[0])
    def click():
        return {
            "goals": [UndeterminedIntervalExchangeTransformation],
        }

    def command(self):
        return ["undetermined-iet"]

    def _consume(self, decomposition, cost):
        r"""
        Track any undetermined IETs in this ``decomposition``.

        EXAMPLES::

            >>> TODO

        """
        for component in decomposition.decomposition.components():
            if (component.withoutPeriodicTrajectory()):
                continue
            if (component.cylinder()):
                continue

            iet = component.intervalExchangeTransformation().intervalExchangeTransformation()
            # We cannot pickle the original iet because its lengths reference back to the flow decomposition and we cannot pickle that yet.
            # So we forget that connection and create a new IET from scratch.
            # That is also (unfortunately) important so pyintervalxt learn
            # about the lengths involved and registers the serialization code
            # correctly.
            construction = cppyy.gbl.construction(iet)
            degree = construction[0][0].parent().degree()
            iet = pyintervalxt.IntervalExchangeTransformation(list(construction[0]), list(construction[1]))
            self._report.result(self, iet, degree=degree, intervals=len(construction[0]))

        return not Consumer.COMPLETED

    def deform(self, deformation):
        return {
            "goals": [UndeterminedIntervalExchangeTransformation],
        }

    @classmethod
    def reduce(self, results):
        r"""
        Given a list of historic results, return a final verdict.

        EXAMPLES::

            >>> TODO

        """
        return None
