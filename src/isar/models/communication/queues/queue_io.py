from queue import Queue


class QueueIO:
    """
    Creates input and output queue. The queues are defined such that input is from api to state machine
    while output is from state machine to api.
    """

    def __init__(self, input_size: int = 0, output_size: int = 0):
        self.input: Queue = Queue(maxsize=input_size)
        self.output: Queue = Queue(maxsize=output_size)
