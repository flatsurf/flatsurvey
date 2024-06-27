import multiprocessing

forkserver = multiprocessing.get_context("forkserver")
multiprocessing.set_forkserver_preload(["sage.all"])


class DaskTask:
    def __init__(self, callable, *args, **kwargs):
        from pickle import dumps
        self._dump = dumps((callable, args, kwargs))

    def __call__(self):
        DaskWorker.process(self)

    def run(self):
        from pickle import loads
        callable, args, kwargs =loads(self._dump)

        import asyncio
        result = asyncio.run(callable(*args, **kwargs))
        print(result)
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
        import sys
        if 'sage' in sys.modules:
            raise Exception("sage must not be loaded in dask worker")

        if DaskWorker._singleton is None:
            DaskWorker._singleton = DaskWorker()

    @staticmethod
    def _process(self):
        while True:
            try:
                task = self._work_queue.get()
            except ValueError:
                break
            print(task)

            self._result_queue.put(task.run())
            print("done.")

    @staticmethod
    def process(task):
        DaskWorker._ensure_started()
        DaskWorker._singleton._work_queue.put(task)
        return DaskWorker._singleton._result_queue.get()
