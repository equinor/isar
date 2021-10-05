from configparser import ConfigParser
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from isar.config.configuration_error import ConfigurationError


class Config(object):
    def __init__(self):
        load_dotenv()
        env = getenv("ENVIRONMENT")
        if not env:
            raise ConfigurationError(f"Environment not set")
        self.parser = ConfigParser()

        cwd: Path = Path.cwd()
        default_config: Path
        env_config: Path

        # The Azure Pipelines job is unable to import with the same script as it starts to search in site-packages.
        # This if-statement is a workaround to enable running locally, from a robot package and in the pipeline.
        if str(cwd) == "/home/vsts/work/1/s":
            print("Running in Azure Pipelines")
            default_config: Path = Path("./src/isar/config/default.ini")
            env_config: Path = Path(f"./src/isar/config/{env}.ini")
        else:
            print("Running somewhere else")
            default_config: Path = Path(
                f"{Path(__file__).parent.resolve()}/default.ini"
            )
            env_config: Path = Path(f"{Path(__file__).parent.resolve()}/{env}.ini")

        found_default: bool = self.parser.read(default_config)
        found_env: bool = self.parser.read(env_config)
        print(f"Default config: {default_config}")
        if not found_default or not found_env:
            raise ConfigurationError(
                f"Failed to import configuration, default: {found_default}, env: {found_env}"
            )

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
