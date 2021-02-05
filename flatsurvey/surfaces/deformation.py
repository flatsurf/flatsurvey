#*********************************************************************
#  This file is part of flatsurf.
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
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

from .surface import Surface

from flatsurvey.pipeline.util import FactoryBindingSpec, PartialBindingSpec

import flatsurvey.worker.restart

class Deformation(Surface):
    def __init__(self, deformed, old):
        self._deformed = deformed
        self._old = old

    def __repr__(self):
        return repr(self._old)

    @property
    def _eliminate_marked_points(self):
        return self._old._eliminate_marked_points

    @property
    def orbit_closure_dimension_upper_bound(self):
        return self._old.orbit_closure_dimension_upper_bound

    def _surface(self):
        return self._deformed

    class Restart(flatsurvey.worker.restart.Restart):
        def __init__(self, deformed, old):
            self._deformation = Deformation(deformed=deformed, old=old)

        def rewrite_bound(self, bound):
            if isinstance(bound, Surface):
                return [ FactoryBindingSpec(name="surface", prototype=lambda: self._deformation) ]

            return bound.deform(deformation=self._deformation)['bindings']

        def rewrite_goal(self, goal, objects):
            goal = objects.provide(goal)
            goals = goal.deform(deformation=self._deformation)['goals']
            if len(goals) != 1:
                raise NotImplementedError
            return goals[0]

        def rewrite_reporter(self, reporter, objects):
            reporter = objects.provide(reporter)
            reporters = reporter.deform(deformation=self._deformation)['reporters']
            if len(reporters) != 1:
                raise NotImplementedError
            return reporters[0]
