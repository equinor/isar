from threading import Thread
from typing import Callable, ParamSpec

P = ParamSpec("P")


class FunctionThread(Thread):
    def __init__(
        self, handler_function: Callable[P, None], *args: P.args, **kwargs: P.kwargs
    ):
        self.handler_function = lambda: handler_function(*args, **kwargs)
        Thread.__init__(self, name="Robot start mission thread")
        self.start()

    def run(self) -> None:
        self.handler_function()
