from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.models.mission_metadata.required_metadata import RequiredMetadata
from isar.models.mission_metadata.recommended_metadata import RecommendedMetadata

mock_required_metadata = RequiredMetadata(
    mission_id="KAAWILLIAM111020211508",
)

mock_recommended_metadata = RecommendedMetadata(
    date="11.10.2021",
)

mock_metadata = MissionMetadata(
    mission_id="KAAWILLIAM111020211508",
    recommended_metadata=mock_recommended_metadata,
)
