r"""
A package providing ways to report progress and result of a computation.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Julian Rüth
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

from flatsurvey.reporting.json import Json
from flatsurvey.reporting.log import Log
from flatsurvey.reporting.report import Report
from flatsurvey.reporting.yaml import Yaml
from flatsurvey.reporting.progress import Progress

commands = [Log.click, Yaml.click, Json.click, Report.click, Progress.click]
