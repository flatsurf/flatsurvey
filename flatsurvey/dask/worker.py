r"""
A module that gets preloaded in each dask worker.

This module works around many oddities and performance problems in using
SageMath in dask.

TESTS:

Importing this module silences cppyy warnings::

    >>> import cppyy

This module provides us with a worker-global forkserver with SageMath preloaded
that is used by the :class:`Runner`.

    >>> forkserver
    <multiprocessing.context.ForkServerContext object at 0x...>

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2024-2025 Julian Rüth
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
import multiprocessing

# We import sage.all before forking off child processes.
# Importing sage.all is very costly, so we import it once in the template
# process that gets then cloned to produce the workers in the fork calls.
forkserver = multiprocessing.get_context("forkserver")
multiprocessing.set_forkserver_preload(["sage.all"])

# Silence warnings from cppyy which is still relying on pkg_resources.
import warnings

warnings.filterwarnings(
    "ignore", module="cppyy", message="pkg_resources is deprecated as an API"
)
