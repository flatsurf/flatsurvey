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

class Services:
    r"""
    A collection of singleton services.
    """
    def __init__(self):
        self._singletons = {}

    def get(self, service, factory=None):
        if factory is None:
            factory = service
        if service not in self._singletons:
            self._singletons[service] = factory
        if callable(self._singletons[service]):
            self._singletons[service] = self._singletons[service](self)
        return self._singletons[service]

    def register(self, key, factory):
        if key in self._singletons:
            raise ValueError("singleton for this key already registered")
        self._singletons[key] = factory
