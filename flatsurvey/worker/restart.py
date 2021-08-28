#*********************************************************************
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
#*********************************************************************

from flatsurvey.pipeline.util import provide

class Restart(Exception):
    def rewrite_command(self, command, objects):
        return {
            "bindings": [self.rewrite_binding(binding, objects=objects) for binding in command.get("bindings", [])],
            "goals": [self.rewrite_goal(goal, objects=objects) for goal in command.get("goals", [])],
            "reporters": [self.rewrite_reporter(reporter, objects=objects) for reporter in command.get("reporters", [])],
        }

    def rewrite_binding(self, binding, objects):
        providers = [provider for provider in dir(binding) if provider.startswith('provide_')]
        if not providers:
            raise NotImplementedError("Cannot rewrite binding that does not provide_ anything")
        if len(providers) >= 2:
            raise NotImplementedError("Cannot rewrite binding that does provide_ more than one object")
        
        bound = provide(providers[0][len("provide_"):], objects)

        bindings = self.rewrite_bound(bound)

        if len(bindings) != 1:
            raise NotImplementedError

        return bindings[0]

    def rewrite_goal(self, goal, objects):
        raise NotImplementedError

    def rewrite_reporter(self, reporter, objects):
        raise NotImplementedError

    def rewrite_bound(self, bound):
        raise NotImplementedError
