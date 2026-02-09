# This file uses SQLAlchemy to interface the persistent database storage.

from enum import Enum as EnumClass
from typing import Optional

import sqlalchemy
from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class RobotStartupMode(EnumClass):
    Normal = "Normal"
    Maintenance = "Maintenance"
    Lockdown = "Lockdown"


class PersistentRobotState(Base):
    __tablename__ = "persistent_robot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(64))
    robot_startup_mode: Mapped[RobotStartupMode] = mapped_column(
        Enum(RobotStartupMode), nullable=False, default=RobotStartupMode.Normal
    )

    def __repr__(self) -> str:
        return f"PersistentRobotState(id={self.id!r}, robot_id={self.robot_id!r}, robot_startup_mode={self.robot_startup_mode.value!r})"


class NoSuchRobotException(Exception):
    pass


def read_persistent_robot_state(
    connection_string: str, robot_id: str
) -> RobotStartupMode:
    engine = sqlalchemy.create_engine(connection_string)

    with Session(engine) as session:
        statement = sqlalchemy.select(PersistentRobotState).where(
            PersistentRobotState.robot_id == robot_id
        )
        read_persistent_state = session.scalar(statement)

        if read_persistent_state is None:
            raise NoSuchRobotException(
                f"No robot in persistent storage with id {robot_id}"
            )

        return read_persistent_state.robot_startup_mode


def change_persistent_robot_state(
    connection_string: str, robot_id: str, value: RobotStartupMode
) -> None:
    engine = sqlalchemy.create_engine(connection_string)

    with Session(engine) as session:
        statement = sqlalchemy.select(PersistentRobotState).where(
            PersistentRobotState.robot_id == robot_id
        )
        read_persistent_state: Optional[PersistentRobotState] = session.scalar(
            statement
        )

        if read_persistent_state is None:
            raise ValueError("Could not read missing column 'Lockdown mode'")

        read_persistent_state.robot_startup_mode = value
        session.commit()


def create_persistent_robot_state(
    connection_string: str, robot_id: str, startup_mode: RobotStartupMode
) -> None:
    engine = sqlalchemy.create_engine(connection_string)

    with Session(engine) as session:
        persistent_state = PersistentRobotState(
            robot_id=robot_id, robot_startup_mode=startup_mode
        )
        session.add_all([persistent_state])
        session.commit()
