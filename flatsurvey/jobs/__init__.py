r"""
Steps along the pipeline to resolve the targets of a survey.

These steps are automatically registered as commands to the survey and worker
entrypoints as subcommands.
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
from .orbit_closure import OrbitClosure
from .flow_decomposition import FlowDecompositions
from .saddle_connections import SaddleConnections
from .saddle_connection_orientations import SaddleConnectionOrientations
from .completely_cylinder_periodic import CompletelyCylinderPeriodic
from .completely_cylinder_periodic_asymptotics import CompletelyCylinderPeriodicAsymptotics
from .cylinder_periodic_direction import CylinderPeriodicDirection
from .undetermined_interval_exchange_transformation import UndeterminedIntervalExchangeTransformation

commands = [OrbitClosure.click, CylinderPeriodicDirection.click, CompletelyCylinderPeriodic.click, FlowDecompositions.click, CompletelyCylinderPeriodic.click, CompletelyCylinderPeriodicAsymptotics.click, SaddleConnections.click, SaddleConnectionOrientations.click, UndeterminedIntervalExchangeTransformation.click]
