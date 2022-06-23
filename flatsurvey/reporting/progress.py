r"""
TODO
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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

# TODO: Inline imports
import rich.progress
import rich.live
import rich.console
import rich.panel
import rich.padding
import click

from flatsurvey.command import Command
from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.reporting.reporter import Reporter


class Progress(Reporter, Command):
    r"""
    TODO
    """

    def __init__(self, source=None, parent=None):
        self._activities = []

        import threading
        self._rlock = threading.RLock()

        self._dirty = True

        self._source = source
        self._parent = parent

        self._title = None
        self._activity = ""
        self._count = None
        self._total = None
        self._what = None
        self._message = ""

        self._visualization = rich.console.Group()
        self._progress = rich.progress.Progress()
        self._start_time = self._progress.get_time()
        self._create_task()

        self._visible = True

    # The global singleton live display that is currently active.
    _live = None

    @classmethod
    def enable(cls, self):
        root = self

        while root._parent is not None:
            root = root._parent

        if cls._live is None:
            cls._live = rich.live.Live(rich.console.Group("…"))
            cls._live.start()
            cls._live._owner = root

        assert cls._live._owner is root

        return cls._live

    @classmethod
    def disable(cls, self):
        assert cls._live._owner is self

        cls._live.stop()
        cls._live = None

    @classmethod
    @click.command(
        name="progress",
        cls=GroupedCommand,
        group="Reports",
        help=__doc__.split("EXAMPLES")[0],
    )
    def click():
        return {
            "bindings": [PartialBindingSpec(Progress, scope="SHARED")()],
            "reporters": [Progress],
        }

    def command(self):
        return ["progress"]

    def progress(self, source, count=None, advance=None, total=None, what=None, message=None, parent=None, activity=None):
        with self._rlock:
            _activity = self._get_activity(source, parent=parent, create=True)
            _activity.update(count=count, advance=advance, what=what, total=total, message=message, activity=activity)
            return _activity

    def __enter__(self):
        if self._visible is True:
            self._visible = 0

        assert self._visible >= 0

        self._visible += 1

    def __exit__(self, *exc):
        assert self._visible is not True
        assert self._visible >= 1
        assert self._parent is not None

        self._visible -= 1

        if self._visible == 0:
            self._parent._dirty = True
            self._parent.redraw()

    def _get_activity(self, source, parent=None, create=False):
        def get(self):
            if self._source == parent:
                # activity must be one of our child activities
                for activity in self._activities:
                    if activity._source == source:
                        return activity

                if not create:
                    return None

                activity = Progress(source=source, parent=self)
                self._activities.append(activity)

                self._dirty = True
                self.redraw()

                return activity

            for activity in self._activities:
                match = get(activity)
                if match is not None:
                    return match

        activity = get(self)

        assert not create or activity is not None, f"no activity with source {parent}"

        return activity

    def redraw(self):
        live = Progress.enable(self)

        if self._dirty:
            self._dirty = False

            self._redraw()

            if self._parent is not None:
                self._parent._dirty = True
                self._parent.redraw()
            else:
                live.update(self._visualization)

        return self._visualization

    def _redraw(self):
        self._activities = [activity for activity in self._activities if activity._visible]

        if self._parent is None:
            if not self._activities:
                Progress.disable(self)
                return

            self._visualization = rich.console.Group(*[activity.redraw() for activity in self._activities])
        else:
            panel = self._parent._parent is None and self._parent._activities != [self]

            if panel:
                progress_columns = ["{task.description}"]
                if self._total:
                    progress_columns.append(rich.progress.BarColumn())
                else:
                    progress_columns.append(rich.progress.SpinnerColumn())

                if self._total is None:
                    if self._what and self._count is not None:
                        progress_columns.append("[gray37]({task.completed} {task.fields[what]})")
                else:
                    if self._what and self._count is not None:
                        progress_columns.append("[grey37]({task.completed}/{task.total} {task.fields[what]})")

                progress_columns.append(rich.progress.TimeElapsedColumn())

                self._progress = rich.progress.Progress(*progress_columns)

                self._create_task()

                content = [Progress.ConditionalRenderable(
                    lambda: self._message,
                    Progress.LambdaRenderable(lambda: f"[blue]{self._message}"))]

                if self._activities:
                    content.append(rich.padding.Padding(
                        rich.console.Group(*[child.redraw() for child in self._activities]),
                        (0, 0, 0, 2)))

                self._visualization = rich.panel.Panel(rich.console.Group(self._progress, *content), title=self._title or "")
            elif self._total:
                progress_columns = ["[green]{task.description}", rich.progress.BarColumn()]
                if self._what:
                    progress_columns.append("[grey37]({task.completed}/{task.total} {task.fields[what]})")
                progress_columns.append(rich.progress.TimeElapsedColumn())

                self._progress = rich.progress.Progress(*progress_columns)

                self._create_task()

                visualization = [self._progress]

                visualization.append(Progress.ConditionalRenderable(
                    lambda: self._message,
                    rich.padding.Padding(
                        Progress.LambdaRenderable(lambda: f"[blue]{self._message}"),
                        (0, 0, 0, 2))))

                if self._activities:
                    visualization.append(rich.padding.Padding(
                        rich.console.Group(*[child.redraw() for child in self._activities]),
                        (0, 0, 0, 2)))

                self._visualization = rich.console.Group(*visualization)
            else:
                message = Progress.ConditionalRenderable(
                    lambda: self._message,
                    rich.padding.Padding(
                        Progress.LambdaRenderable(lambda: f"[blue]{self._message}"),
                        (0, 0, 0, 2)))

                progress_columns = [
                    "[green]{task.description}",
                    rich.progress.SpinnerColumn(),
                ]
                if self._what and self._count is not None:
                    progress_columns.append("[gray37]({task.completed} {task.fields[what]})")

                progress_columns.append(rich.progress.RenderableColumn(message))

                self._progress = rich.progress.Progress(*progress_columns)

                self._create_task()

                visualization = [self._progress]

                if self._activities:
                    visualization.append(rich.padding.Padding(
                        rich.console.Group(*[child.redraw() for child in self._activities]),
                        (0, 0, 0, 2)))

                self._visualization = rich.console.Group(*visualization)

    class ConditionalRenderable:
        def __init__(self, predicate, child):
            self._predicate = predicate
            self._child = child

        def __rich_console__(self, console, options):
            if self._predicate():
                return [self._child]
            return []

    class LambdaRenderable:
        def __init__(self, child):
            self._child = child

        def __rich_console__(self, console, options):
            return [self._child()]

    def _create_task(self):
        self._task = self._progress.add_task(self._activity, message=self._message, total=self._total, what=self._what, completed=self._count or 0)
        self._progress.tasks[self._task].start_time = self._start_time

    def update(self, count=None, advance=None, total=None, what=None, message=None, activity=None):
        if count is not None and advance is not None:
            raise ValueError("not both, count and advance can be given")

        if count is not None:
            if self._count is None:
                self._dirty = True

            self._count = count
            self._progress.update(self._task, completed=count)

        if advance is not None:
            self._count = self._count + advance
            self._progress.advance(self._task, advance=advance)

        if total is not None:
            if self._total is None:
                self._dirty = True

            self._total = total
            self._progress.update(self._task, total=total)

        if what is not None:
            self._what = what

            if self._what is None:
                self._dirty = True

            self._progress.update(self._task, what=what)

        if message is not None:
            self._message = message
            self._progress.update(self._task, message=message)

        if activity is not None:
            if self._title is None:
                self._title = activity
                self._dirty = True

            self._activity = activity
            self._progress.update(self._task, description=activity)

        self.redraw()
