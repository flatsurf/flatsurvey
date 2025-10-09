r"""
Progress tracking during surveys
"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2025 Julian Rüth
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

from abc import abstractmethod
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from alive_progress import alive_bar


class Progress(AbstractContextManager):
    r"""
    Abstract base class for progress indicators.

    The indicator is active while the context is active.

    EXAMPLES::

        >>> with Progress.create() as progress:
        ...     progress.set_activity("queueing tasks")
        ...     progress.queued()
        ...     progress.completed()
        queueing tasks |████████████████████████████████████████| 1 in 0.0s ...

    ::

        >>> isinstance(progress, Progress)
        True

    """

    @staticmethod
    @contextmanager
    def create(stdout=True):
        if stdout:
            progress = StdoutProgress("-")
        else:
            progress = SilentProgress()

        with progress as progress:
            yield progress

    @abstractmethod
    def queued(self):
        r"""
        Register that a task was queued (it may or may not be executing
        already.)

        EXAMPLES::

            >>> with Progress.create() as progress:
            ...     progress.queued()
            - |████████████████████████████████████████| 0 in 0.0s ...

        """

    @abstractmethod
    def completed(self):
        r"""
        Register that a previously queued task has run to completion.

        EXAMPLES::

            >>> with Progress.create() as progress:
            ...     progress.queued()
            ...     progress.completed()
            - |████████████████████████████████████████| 1 in 0.0s ...


        """

    @abstractmethod
    def set_activity(self, activity: str):
        r"""
        Set the title of the progress indicator to ``activity``.

        EXAMPLES::

            >>> with Progress.create() as progress:
            ...      progress.set_activity("hello")
            ...      progress.set_activity("world")
            world |████████████████████████████████████████| 0 in 0.0s ...

        """


class SilentProgress(Progress):
    r"""
    A progress indicator that does not display any progress. All methods are
    just nops.

    EXAMPLES::

        >>> with Progress.create(stdout=False) as progress:
        ...     progress.set_activity("activity")
        ...     progress.queued()
        ...     progress.completed()

    ::

        >>> isinstance(progress, SilentProgress)
        True

    """

    def queued(self):
        pass

    def completed(self):
        pass

    def set_activity(self, activity: str):
        del activity

    def __exit__(self, *exc):
        del exc


class StdoutProgress(Progress):
    r"""
    A simple text based progress indicator that is visible while its context is
    active.

    EXAMPLES::

        >>> with Progress.create(stdout=True) as progress:
        ...     progress.set_activity("activity")
        ...     progress.queued()
        ...     progress.completed()
        activity |████████████████████████████████████████| 1 in 0.0s ...

    ::

        >>> isinstance(progress, StdoutProgress)
        True

    """

    def __init__(self, activity: str):
        self._bar = alive_bar(title=activity)
        self._context: Any = None
        self._queued = 0
        self._scheduled = 0

    def _update_text(self):
        self._context.text(f"{self._queued} pending")

    def queued(self):
        self._queued += 1
        self._update_text()

    def completed(self):
        self._queued -= 1
        self._update_text()
        self._context()

    def set_activity(self, activity):
        self._context.title(activity)

    def __enter__(self):
        self._context = self._bar.__enter__()
        self._update_text()
        return self

    def __exit__(self, *exc):
        self._context = None
        self._bar.__exit__(*exc)
