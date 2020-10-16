import sys
import click

from pinject import copy_args_to_internal_fields

from flatsurvey.ui.group import GroupedCommand

from .report import Reporter

from flatsurvey.pipeline.util import FactoryBindingSpec

class Log(Reporter):
    r"""
    Write results and progress to a log file.
    """
    @copy_args_to_internal_fields
    def __init__(self, surface, stream=None):
        self._stream = stream or sys.stdout

    def _prefix(self, source):
        return f"[{self._surface}] [{type(source).__name__}]"

    def _log(self, message):
        self._stream.write("%s\n"%(message,))
        self._stream.flush()

    def log(self, source, message, **kwargs):
        message = f"{self._prefix(source)} {message}"
        for k,v in kwargs.items():
            message += f" {k}: {v}"
        self._log(message)

    def progress(self, source, unit, count, total=None):
        self.log(source, f"{unit}: {count}/{total or '?'}")

    def result(self, source, result, **kwargs):
        shruggie = r'¯\_(ツ)_/¯'
        self.log(source, shruggie if result is None else result)

    def command(self):
        if self._stream is sys.stdout: output = []
        else: output = ["--output", self._stream.name]
        return ["log"] + output


@click.command(name="log", cls=GroupedCommand, group="Reports", help=Log.__doc__)
@click.option("--output", type=click.File("w"), default=None)
def log(output):
    return FactoryBindingSpec("log", lambda surface: Log(surface, stream or open("%s.log"%surface._name, "w")))
