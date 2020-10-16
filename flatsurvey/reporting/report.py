class Report:
    def __init__(self, reporters):
        self._reporters = reporters

    def log(self, source, message, **kwargs):
        r"""
        Write an informational message to the log.
        """
        for reporter in self._reporters:
            reporter.log(source, message, **kwargs)

    def result(self, source, result, **kwargs):
        r"""
        Report a final ``result`` of a computation ``source``. Such a result
        can have been explicitly ``requested`` by the user or just be a
        by-product of the computation.
        """
        for reporter in self._reporters:
            reporter.result(source, result, **kwargs)

    def progress(self, source, unit, count, total=None):
        r"""
        Report that some progress has been made in the resolution of the
        computation ``source``. Now we are at ``count`` of ``total`` given in
        multiples of ``unit``.
        """
        for reporter in self._reporters:
            reporter.progress(source, unit, count, total)

class Reporter:
    def log(self, source, message, **kwargs): pass
    def result(self, source, result, **kwargs): pass
    def progress(self, source, unit, count, total=None): pass
    def flush(self): pass
