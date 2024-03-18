# Copyright (C) 2024 twyleg
import logging
import json
import os

import jsonschema

from typing import List, Optional, Dict, Iterator
from pathlib import Path

from github.PaginatedList import PaginatedList
from github.Repository import Repository


CLASSROOM_UTILS_CONFIG_FILE_SEARCH_PATHS = [
    Path.cwd() / "classroom_utils_config.json",
    Path.cwd().parent / "classroom_utils_config.json"
]
CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME = "CLASSROOM_UTILS_CONFIG"

FILE_DIR = Path(__file__).parent
CLASSROOM_UTILS_CONFIG_FILE_SCHEMA = FILE_DIR / "resources/schemas/classroom_utils_schema.json"


class GithubUser:
    def __init__(self, name: str, surname: str, github_username: str, active: bool):
        self.name = name
        self.surname = surname
        self.github_username = github_username
        self.active = active

    def __repr__(self):
        return f"name='{self.name}', surname='{self.surname}', github_username='{self.github_username}', active='{self.active}"

    @property
    def fullname(self) -> str:
        return f"{self.surname} {self.name}"


class Member(GithubUser):
    pass


class Moderator(GithubUser):
    pass


class Class:
    def __init__(self, name: str, members: Optional[List[Member]] = None, moderators: Optional[List[Moderator]] = None):
        self.name = name
        if members is None:
            members = []
        self.members = members

        if moderators is None:
            moderators = []
        self.moderators = moderators

    def append_member(self, student: Member):
        self.members.append(student)

    def append_moderator(self, moderator: Moderator):
        self.moderators.append(moderator)

    @property
    def active_members(self) -> Iterator[Member]:
        for member in self.members:
            if member.active:
                yield member

    @property
    def inactive_members(self) -> Iterator[Member]:
        for member in self.members:
            if not member.active:
                yield member

    def __repr__(self):
        return f"name='{self.name}', members='{str(self.members)}'"


class ClassroomUtilsConfigNotFoundError(Exception):
    pass


def find_classroom_utils_config_file() -> Path:
    logging.debug("Searching classroom_utils config file")

    logging.debug("Checking %d search paths:", len(CLASSROOM_UTILS_CONFIG_FILE_SEARCH_PATHS))
    for search_path in CLASSROOM_UTILS_CONFIG_FILE_SEARCH_PATHS:
        logging.debug("Checking path: %s", search_path)
        if search_path.exists():
            logging.debug("Config file found!")
            return search_path
        else:
            logging.debug("Config file not found!")

    logging.debug("Checking environment variable '%s':", CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME)
    if CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME in os.environ:
        config_file_path = Path(os.environ[CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME])
        logging.debug("Checking path: %s", config_file_path)
        if config_file_path.exists():
            logging.debug("Config file found!")
            return config_file_path
        else:
            logging.debug("Config file not found!")
    else:
        logging.debug("Environment variable '%s' not provided", CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME)

    raise ClassroomUtilsConfigNotFoundError(f"Unable to find config file in any of the given search paths "
                                            f"({CLASSROOM_UTILS_CONFIG_FILE_SEARCH_PATHS}) or the environment variable "
                                            f"({CLASSROOM_UTILS_CONFIG_FILE_ENVIRONMENT_VARIABLE_NAME})")


def validate_classroom_utils_config_file(classroom_utils_config_filepath: Path) -> bool:
    with open(CLASSROOM_UTILS_CONFIG_FILE_SCHEMA) as json_schema_file:
        json_schema = json.load(json_schema_file)

        with open(classroom_utils_config_filepath) as class_definition_file:
            class_definition_dict = json.load(class_definition_file)
            jsonschema.validate(instance=class_definition_dict, schema=json_schema)


def read_classes_from_config(classroom_utils_config_filepath: Path | None = None) -> Dict[str, Class]:

    if classroom_utils_config_filepath is None:
        classroom_utils_config_filepath = find_classroom_utils_config_file()

    validate_classroom_utils_config_file(classroom_utils_config_filepath)
    with open(classroom_utils_config_filepath, encoding="utf-8") as classroom_utils_config_file:
        class_definition_dict = json.load(classroom_utils_config_file)

        classes: Dict[str, Class] = {}

        for class_name, class_dict in class_definition_dict["classes"].items():
            class_ = Class(class_name)
            classes[class_name] = class_

            class_members = class_dict["members"]
            for class_member in class_members:
                student = Member(class_member["name"], class_member["surname"], class_member["github_username"],
                                 class_member.get("active", True))
                class_.append_member(student)

            class_moderators = class_dict["moderators"]
            for class_moderator in class_moderators:
                moderator = Moderator(class_moderator["name"], class_moderator["surname"],
                                      class_moderator["github_username"], class_moderator.get("active", True))
                class_.append_moderator(moderator)

        return classes


def get_class_by_name(class_name: str, classes: Dict[str, Class] | None = None) -> Class:

    if classes is None:
        classes = read_classes_from_config()

    requsted_class = classes[class_name]

    logging.debug("Class: name='%s'", class_name)
    logging.debug("  members:")
    for member in requsted_class.members:
        logging.debug("    - Student: %s", member)
    logging.debug("  moderators:")
    for moderator in requsted_class.moderators:
        logging.debug("    - Moderator: %s", moderator)

    return classes[class_name]


def generate_personal_repo_name(class_member: Member, prefix: str | None = None):
    def normalize(text: str) -> str:
        return text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "sz")

    name = normalize(class_member.name)
    surname = normalize(class_member.surname)

    if prefix:
        return f"{prefix}_{name}_{surname}"
    else:
        return f"{name}_{surname}"


def find_personal_repo(student: Member, repos: PaginatedList[Repository]) -> Repository | None:
    minimal_repo_name = generate_personal_repo_name(student)

    for repo in repos:
        if minimal_repo_name in repo.name:
            return repo
    return None
