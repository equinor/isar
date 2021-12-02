from typing import Tuple

from robot_interface.robot_interface import RobotInterface


def interface_test(Robot: RobotInterface) -> None:
    for func in dir(RobotInterface):
        if not callable(getattr(Robot, func)) or func.startswith("__"):
            continue

        arg_robot: int = getattr(Robot, func).__code__.co_argcount
        arg_isar: int = getattr(RobotInterface, func).__code__.co_argcount

        args_robot: Tuple[str] = getattr(Robot, func).__code__.co_varnames[:arg_robot]
        args_isar: Tuple[str] = getattr(RobotInterface, func).__code__.co_varnames[
            :arg_isar
        ]

        assert arg_robot == arg_isar
        assert args_robot == args_isar
