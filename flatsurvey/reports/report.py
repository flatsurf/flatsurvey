class Report:
    def __init__(self, reporters):
        self._reporters = reporters

    def log(self, source, message, **kwargs):
        for reporter in self._reporters:
            reporter.log(source, message, **kwargs)

    def update(self, source, result, **kwargs):
        for reporter in self._reporters:
            reporter.update(source, result, **kwargs)

    def partial(self, source, result, **kwargs):
        for reporter in self._reporters:
            reporter.partial(source, result, **kwargs)

    def progress(self, source, unit, count, total=None):
        for reporter in self._reporters:
            reporter.progress(source, unit, count, total)

class Reporter:
    def log(self, source, message, **kwargs): pass
    def update(self, source, result, **kwargs): pass
    def partial(self, source, result, **kwargs): pass
    def progress(self, source, unit, count, total=None): pass
    def flush(self): pass
