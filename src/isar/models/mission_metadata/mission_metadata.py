from dataclasses import InitVar, dataclass, field, replace
from datetime import datetime
from typing import Union
from uuid import UUID
from isar.models.mission_metadata import additional_metadata

from isar.models.mission_metadata.additional_metadata import (
    AdditionalMetadata,
    map_echo_hub_api_to_metadata_keys,
)
from isar.models.mission_metadata.recommended_metadata import RecommendedMetadata
from isar.models.mission_metadata.required_metadata import RequiredMetadata


@dataclass
class MissionMetadata:
    mission_id: InitVar[Union[UUID, int, str, None]] = None
    required_metadata: RequiredMetadata = field(init=False)
    recommended_metadata: RecommendedMetadata = RecommendedMetadata()
    additional_metadata: AdditionalMetadata = AdditionalMetadata()

    def __post_init__(self, mission_id: str) -> None:
        if mission_id is not None:
            self.required_metadata = RequiredMetadata(mission_id=mission_id)

        if self.recommended_metadata.date is None:
            now: datetime = datetime.utcnow()
            self.recommended_metadata.date = f"{now.day}.{now.month}.{now.year}"

    def update_metadata(self, mission_plan: dict):
        """
        Update additional metadata with certain fields from the mission plan from Echo. A
        renaming of the fields coming from Echo is done to match the fields in SLIMM.
        """
        updated_additional_metadata = self._key_selection_and_mapping(
            mission_plan, map_echo_hub_api_to_metadata_keys
        )
        self.additional_metadata = replace(
            self.additional_metadata, **updated_additional_metadata
        )

    def _key_selection_and_mapping(self, original: dict, map_keys: dict) -> dict:
        """
        Choose desired fields and rename fields
        """
        return {
            map_keys[key]: original[key] for key in map_keys.keys() & original.keys()
        }
