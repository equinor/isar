from isar.models.communication.queues.queue_io import QueueIO


class Queues:
    def __init__(self):
        self.start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.mission_status: QueueIO = QueueIO()
        self.single_action: QueueIO = QueueIO(input_size=1, output_size=1)
