r"""
Possible targets that can be resolved during a survey.

These targets are automatically registered as commands to the survey and worker
entrypoints as subcommands.
"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************
from .orbit_closure import orbit_closure
from .flow_decomposition import cylinder_periodic_direction, completely_cylinder_periodic

goals = [orbit_closure, cylinder_periodic_direction, completely_cylinder_periodic]
