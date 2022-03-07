r"""
The goal of a survey.

A goal is a specialized :class:`Consumer` that is typically not a
:class:`Producer` at the same time and form its verdict from cached previous
runs.

EXAMPLES:

    >>> from flatsurvey.jobs import OrbitClosure
    >>> Goal in OrbitClosure.mro()
    True

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

import click

from flatsurvey.pipeline.consumer import Consumer
from pinject import copy_args_to_internal_fields


class Goal(Consumer):
    r"""
    In the pipeline graph of jobs, a Goal is just a :class:`Consumer` with some
    added facilities that are shared by all actual goals. In practice this
    means that all consumers that are not a :class:`Producer` at the same time
    should most likely inherit from Goal.

    EXAMPLES::

        >>> from flatsurvey.surfaces import Ngon
        >>> from flatsurvey.reporting import Report
        >>> from flatsurvey.jobs import FlowDecompositions, SaddleConnectionOrientations, SaddleConnections
        >>> from flatsurvey.cache import Cache
        >>> from flatsurvey.jobs.orbit_closure import OrbitClosure
        >>> surface = Ngon((1, 1, 1))
        >>> connections = SaddleConnections(surface)
        >>> flow_decompositions = FlowDecompositions(surface=surface, report=Report([]), saddle_connection_orientations=SaddleConnectionOrientations(connections))
        >>> goal = OrbitClosure(surface=surface, report=Report([]), flow_decompositions=flow_decompositions, saddle_connections=connections, cache=Cache())
        >>> isinstance(goal, Goal)
        True

    """
    DEFAULT_CACHE_ONLY = False

    _cache_only_option = click.option(
        "--cache-only",
        default=DEFAULT_CACHE_ONLY,
        is_flag=True,
        help="Do not perform any computation. Only query the cache.",
    )

    @copy_args_to_internal_fields
    def __init__(self, producers, cache, cache_only=DEFAULT_CACHE_ONLY):
        super().__init__(producers=producers)
