from threading import Lock, Thread
from typing import Any, Optional


class ThreadedRequest:
    def __init__(self, request_func: Any) -> None:
        self._thread: Optional[Thread] = None
        self._request_func: Any = request_func
        self._output: Any = None
        self._output_lock: Lock = Lock()

    def start_thread(self, *request_args) -> bool:
        if self._is_thread_alive():
            return False
        self._output = None
        self._thread = Thread(target=self._thread_func, args=request_args)
        self._thread.start()
        return True

    def _is_thread_alive(self) -> bool:
        if not self._thread:
            return False
        return self._thread.is_alive()

    def get_output(self) -> Any:
        if self._is_thread_alive():
            raise ThreadedRequestNotFinishedError
        self._output_lock.acquire()
        output = self._output
        self._output_lock.release()
        if not output:
            raise ThreadedRequestUnexpectedError
        return output

    def wait_for_thread(self) -> None:
        if not self._thread:
            return
        self._thread.join()

    def _thread_func(self, *args) -> None:
        request_output: Any = self._request_func(*args)
        self._output_lock.acquire()
        self._output = request_output
        self._output_lock.release()


class ThreadedRequestError(Exception):
    pass


class ThreadedRequestNotFinishedError(ThreadedRequestError):
    pass


class ThreadedRequestUnexpectedError(ThreadedRequestError):
    pass
