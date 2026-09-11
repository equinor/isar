import logging
import time
from datetime import UTC, datetime
from threading import Thread

from isar.apis.models.models import MissionStartResponse
from isar.config.settings import settings
from isar.models.events import APIEvent, Event, Events
from isar.models.mqtt_queue import MQTTQueue
from robot_interface.models.mission.mission import Mission
from robot_interface.telemetry.payloads import MissionQueuePayload


class MissionQueueService(Thread):
    def __init__(
        self,
        events: Events,
    ):
        self.logger = logging.getLogger("robot")
        self.schedule_mission_event: APIEvent[Mission, MissionStartResponse] = (
            events.api_requests.schedule_mission
        )
        self.mission_ready_event: Event[Mission] = events.async_events.mission_ready
        self.signal_exit: Event = events.signal_state_machine_exit
        self.mqtt_queue: MQTTQueue = events.mqtt_queue
        Thread.__init__(self, name="Mission Queue Service thread")

    def stop(self) -> None:
        return

    def run(self) -> None:

        mission_queue: Event[Mission] = Event(
            "mission_queue", maxsize=settings.MISSION_QUEUE_MAX_SIZE
        )

        while not self.signal_exit.has_event():

            time.sleep(settings.MISSION_QUEUE_REFRESH_INTERVAL)

            payload: MissionQueuePayload = MissionQueuePayload(
                isar_id=settings.ISAR_ID,
                robot_name=settings.ROBOT_NAME,
                mission_queue=list(mission_queue.queue),
            )

            self.mqtt_queue.publish(
                topic=settings.TOPIC_ISAR_MISSION_QUEUE,
                payload=payload.model_dump_json(),
            )

            requested_mission = self.schedule_mission_event.request.consume_event()
            if requested_mission is not None:
                if mission_queue.full():
                    self.schedule_mission_event.trigger_response(
                        MissionStartResponse(
                            mission_scheduled=False,
                            mission_not_scheduled_reason="Mission queue is full",
                        )
                    )
                else:
                    mission_queue.trigger_event(requested_mission)
                    # TODO: use insertion sort for appending it to the queue using start time. Start time None is prioritised. Existing missions are prioritised
                    self.schedule_mission_event.trigger_response(
                        MissionStartResponse(mission_scheduled=True)
                    )

            if self.mission_ready_event.has_event():
                continue

            pending_mission = mission_queue.check()
            if pending_mission is not None and (
                pending_mission.start_time is None
                or pending_mission.start_time > datetime.now(UTC)
            ):
                pending_mission = mission_queue.consume_event()
                if pending_mission is None:
                    self.logger.warning(
                        "Mission was removed from queue before it could be started"
                    )
                self.mission_ready_event.trigger_event(pending_mission)

        self.logger.info("Exiting robot status thread")
