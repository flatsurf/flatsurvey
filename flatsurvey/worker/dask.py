import multiprocessing
forkserver = multiprocessing.get_context("forkserver")
multiprocessing.set_forkserver_preload(["sage.all"])


class DaskTask:
    def __init__(self, *args, **kwargs):
        from pickle import dumps
        self._dump = dumps((args, kwargs))

    def __call__(self):
        DaskWorker.process(self)

    def run(self):
        from pickle import loads
        args, kwargs =loads(self._dump)

        from flatsurvey.worker.worker import Worker

        import asyncio
        result = asyncio.run(Worker.work(*args, **kwargs))
        return result


class DaskWorker:
    _singleton = None

    def __init__(self):
        assert DaskWorker._singleton is None

        self._work_queue = forkserver.Queue()
        self._result_queue = forkserver.Queue()
        self._processor = forkserver.Process(target=DaskWorker._process, args=(self,), daemon=True)
        self._processor.start()

    @staticmethod
    def _ensure_started():
        if DaskWorker._singleton is not None:
            return

        import sys
        if 'sage' in sys.modules:
            raise Exception("sage must not be loaded in dask worker")

        DaskWorker._singleton = DaskWorker()

    @staticmethod
    def _process(self):
        while True:
            try:
                task = self._work_queue.get()
            except ValueError:
                break

            self._result_queue.put(task.run())

    @staticmethod
    def process(task):
        DaskWorker._ensure_started()
        DaskWorker._singleton._work_queue.put(task)
        return DaskWorker._singleton._result_queue.get()
