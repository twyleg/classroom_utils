# Copyright (C) 2024 twyleg
import json
import logging
import os
from pathlib import Path
from typing import List

import jsonschema

FILE_DIR = Path(__file__).parent

logm = logging.getLogger("config")


class ClassroomUtilsConfigNotFoundError(Exception):
    pass


class Config:

    CONFIG_FILE_SEARCH_PATHS = [
        Path.cwd() / "classroom_utils_config.json",
        Path.cwd().parent / "classroom_utils_config.json",
        Path.home() / "classroom_utils_config.json",
        Path.home() / ".classroom_utils_config.json"
    ]

    CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME = "CLASSROOM_UTILS_CONFIG"

    CONFIG_FILE_SCHEMA = FILE_DIR / "resources/schemas/config_file_schema.json"

    @classmethod
    def find_config_filepath(cls) -> Path:
        logm.debug("Searching classroom_utils config file")

        logm.debug("Checking %d search paths:", len(cls.CONFIG_FILE_SEARCH_PATHS))
        for search_path in cls.CONFIG_FILE_SEARCH_PATHS:
            logm.debug("Checking path: %s", search_path)
            if search_path.exists():
                logm.debug("Config file found!")
                return search_path
            else:
                logm.debug("Config file not found!")

        logm.debug("Checking environment variable '%s':", cls.CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME)
        if cls.CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME in os.environ:
            config_file_path = Path(os.environ[cls.CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME])
            logm.debug("Checking path: %s", config_file_path)
            if config_file_path.exists():
                logm.debug("Config file found!")
                return config_file_path
            else:
                logm.debug("Config file not found!")
        else:
            logm.debug("Environment variable '%s' not provided",
                          cls.CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME)

        raise ClassroomUtilsConfigNotFoundError(f"Unable to find config file in any of the given search paths "
                                                f"({cls.CONFIG_FILE_SEARCH_PATHS}) or the environment variable "
                                                f"({cls.CONFIG_FILE_PATH_ENVIRONMENT_VARIABLE_NAME})")

    def __init__(self):
        self.github_token: str | None = None
        self.github_username: str | None = None
        self.classlist_filepaths: List[Path] = []

    @classmethod
    def _get_absolute_classlist_filepath(cls, config_filepath_str: str, classlist_filepath_str: str) -> Path:
        config_filepath = Path(config_filepath_str)
        classlist_filepath = Path(classlist_filepath_str)
        if classlist_filepath.is_absolute():
            return classlist_filepath
        else:
            return config_filepath.parent / classlist_filepath

    def read_from_file(self, config_filepath: Path) -> None:
        logm.info("Reading config from file: %s", config_filepath)
        with open(self.CONFIG_FILE_SCHEMA) as json_schema_file:
            json_schema = json.load(json_schema_file)

            with open(config_filepath) as config_file:
                config_dict = json.load(config_file)
                jsonschema.validate(instance=config_dict, schema=json_schema)

                self.github_token = config_dict["github_token"]
                self.github_username = config_dict["github_username"]
                self.classlist_filepaths = [self._get_absolute_classlist_filepath(config_filepath, classlist_filepath) for classlist_filepath in config_dict["classlists"]]
