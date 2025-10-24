# This file uses SQLAlchemy to interface the persistent database storage.

import sqlalchemy
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class PersistentRobotState(Base):
    __tablename__ = "persistent_robot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(64))
    is_maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self):
        return f"PersistentRobotState(id={self.id!r}, robot_id={self.robot_id!r}, is_maintenance_mode={self.is_maintenance_mode!r})"


class NoSuchRobotException(Exception):
    pass


def read_persistent_robot_state_is_maintenance_mode(
    connection_string: str, robot_id: str
):
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

        return read_persistent_state.is_maintenance_mode


def change_persistent_robot_state_is_maintenance_mode(
    connection_string: str, robot_id: str, value: bool
):
    engine = sqlalchemy.create_engine(connection_string)

    with Session(engine) as session:
        statement = sqlalchemy.select(PersistentRobotState).where(
            PersistentRobotState.robot_id == robot_id
        )
        read_persistent_state = session.scalar(statement)

        read_persistent_state.is_maintenance_mode = value
        session.commit()


def create_persistent_robot_state(connection_string: str, robot_id: str):
    engine = sqlalchemy.create_engine(connection_string)

    with Session(engine) as session:
        persistent_state = PersistentRobotState(
            robot_id=robot_id, is_maintenance_mode=True
        )
        session.add_all([persistent_state])
        session.commit()
