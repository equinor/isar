from isar.models.communication.queues.queues import Queues


class TestQueues:
    def test_queues(self):
        queues = Queues()
        assert queues.start_mission is not None
        assert (
            queues.start_mission.input is not None
            and queues.start_mission.input.maxsize is 1
        )
        assert (
            queues.start_mission.output is not None
            and queues.start_mission.output.maxsize is 1
        )
        assert queues.stop_mission is not None
        assert (
            queues.stop_mission.input is not None
            and queues.stop_mission.input.maxsize is 1
        )
        assert (
            queues.stop_mission.output is not None
            and queues.stop_mission.output.maxsize is 1
        )
