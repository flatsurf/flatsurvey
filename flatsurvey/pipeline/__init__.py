r"""
A package describing the abstract computation pipeline, i.e., Consumers and Producers.

When computing with translation surfaces it turned out that, starting from a
fixed surface, many computations rely on the same intermediate data. E.g., many
computations require us to sample saddle connections on that surface. Since we
do not want to compute that shared data several times, we organize the
computation in a pipeline, i.e., a graph where the vertices are called
Producers if they are at the source of an edge and Consumers if they are
targeted by an edge. (And Processors when they are both.)
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

from .consumer import Consumer
from .processor import Processor
from .producer import Producer
