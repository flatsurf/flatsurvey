# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
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

from typing import Callable

from flatsurvey.pipeline import Bindings


class Restart(Exception):
    r"""
    An exception that signals that the worker should restart on a modified
    bindings.

    INPUT:

    - ``bindings`` -- a :class:`Bindings` factory which the worker will invoke
      to restart

    .. NOTE::

        Using exception like this for such high-level control flow is a dubious
        pattern to say the least. But it is also very convenient.

    EXAMPLES:

    We attempt an orbit-closure computation for a triangle which is known to
    have non-dense orbit closure. This will lead to a restart throughout the
    process as the system fails to determine whether the orbit closure is
    dense::

        >>> from flatsurvey.test.cli import invoke
        >>> from flatsurvey.worker import worker

        >>> invoke(worker, "ngon", "-a", "1", "-a", "4", "-a", "11", "orbit-closure", "--deform-limit=0", "--limit=2")
        [OrbitClosure] dimension: 3/8
        [OrbitClosure] Found 0 directions with cylinders without a dimension increase. Will attempt to deform the surface to improve the situation.
        ...
        [OrbitClosure] GL(2,R)-orbit closure of dimension at least ... in H_6(10) ... (dense: None) (stratum: H_6(10))

    """

    def __init__(self, create_bindings: Callable[[Bindings], Bindings]):
        super().__init__(f"Restart requested with modified bindings")

        self.create_bindings = create_bindings
