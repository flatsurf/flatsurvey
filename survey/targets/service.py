r"""
Base class for something ressembling a "service" in Dependency Injection jargon

Services for us a simply singletons that are used to satisfy dependencies of
other services, e.g., the saddle connections of a surface are a service that
provides saddle connections and requires a "surface" service.
"""
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

class Service:
    def __init__(self, services):
        self._services = services
        self._targets = []

    def register(self, target):
        r"""
        Register ``target`` as a dependent service.

        When our state changes we call the ``consume`` method of ``target``.
        """
        self._targets.append(target)
        return self

    def _get(self, service):
        r"""
        Resolve ``service`` and register ourselves as a dependency.
        """
        return self._services.get(service).register(self)

    def _notify(self):
        r"""
        Notify all dependent services that our state has changed.
        """
        for target in self._targets:
            target.consume()
