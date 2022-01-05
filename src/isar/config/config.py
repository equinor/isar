import importlib.resources as pkg_resources
from argparse import ArgumentParser
from configparser import ConfigParser
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from isar.config.configuration_error import ConfigurationError


class Args:
    def __init__(self):
        self.parser = ArgumentParser()

        self.parser.add_argument("-s", "--settings-file", default="")
        self.args = self.parser.parse_args()


args = Args().args


class Config:
    def __init__(self):
        load_dotenv()

        self.parser = ConfigParser()

        with pkg_resources.path("isar.config", "default.ini") as filepath:
            found_default: bool = self.parser.read(filepath)

        if not found_default:
            raise ConfigurationError(
                f"Failed to import configuration, default: {found_default}"
            )

        robot_package: str = getenv("ROBOT_PACKAGE")
        if robot_package:
            self.parser.set("DEFAULT", "robot_package", robot_package)

        setting_files: list[str] = [
            "settings.ini",
            args.settings_file,
        ]

        self._read_settings(setting_files)

    def _read_settings(self, filepaths: list[str]) -> list[str]:
        filepaths: list[Path] = [Path(filepath) for filepath in filepaths]
        read_paths: list[str] = self.parser.read(filepaths)

        return read_paths

    def get(self, section, option):
        return self.parser.get(section, option)

    def getint(self, section, option):
        return self.parser.getint(section, option)

    def getfloat(self, section, option):
        return self.parser.getfloat(section, option)

    def getbool(self, section, option):
        return self.parser.getboolean(section, option)

    def sections(self):
        return self.parser.sections()


config = Config().parser
