from isar.models.communication.messages import StartMessage, StopMessage
from isar.models.mission import Mission


class MQTTServiceMock:
    def __init__(
        self,
    ) -> None:
        pass

    def is_connected(self):
        return True

    def time_since_disconnect(self):
        return 0

    def send_start_mission(self, mission: Mission):
        pass

    def send_start_mission_ack(self, start_mission_message: StartMessage):
        pass

    def send_stop_mission(self):
        pass

    def send_stop_mission_ack(self, stop_mission_message: StopMessage):
        pass

    def subscribe_start_mission(self, callback=None):
        pass

    def subscribe_start_mission_ack(self, callback=None):
        pass

    def subscribe_stop_mission(self, callback=None):
        pass

    def subscribe_stop_mission_ack(self, callback=None):
        pass
