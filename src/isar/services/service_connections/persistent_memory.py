# This file uses SQLAlchemy to interface the persistent database storage.

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PersistentRobotState(Base):
    __tablename__ = "persistent_robot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(32))
    is_maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self):
        return f"PersistentRobotState(id={self.id!r}, robot_id={self.robot_id!r}, is_maintenance_mode={self.is_maintenance_mode!r})"
