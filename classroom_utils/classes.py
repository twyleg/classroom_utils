# Copyright (C) 2024 twyleg
import json
import jsonschema

from pathlib import Path
from typing import List, Optional, Dict, Iterator

from github.PaginatedList import PaginatedList
from github.Repository import Repository


FILE_DIR = Path(__file__).parent


class User:
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


class Member(User):

    def generate_personal_repo_name(self, prefix: str | None = None):
        def normalize(text: str) -> str:
            return text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "sz").replace(" ", "_")

        name = normalize(self.name)
        surname = normalize(self.surname)

        if prefix:
            return f"{prefix}_{name}_{surname}"
        else:
            return f"{name}_{surname}"

    def find_personal_repo(self, repos: PaginatedList[Repository]) -> Repository | None:
        minimal_repo_name = self.generate_personal_repo_name()

        for repo in repos:
            if minimal_repo_name in repo.name:
                return repo
        return None


class Moderator(User):
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


class Classes:

    CLASSLIST_FILE_SCHEMA = FILE_DIR / "resources/schemas/classlist_file_schema.json"

    def __init__(self):
        self.classes_by_name: Dict[str, Class] = {}

    def read_classlist_from_file(self, classlist_filepath: Path) -> None:
        with open(self.CLASSLIST_FILE_SCHEMA) as json_schema_file:
            json_schema = json.load(json_schema_file)

            with open(classlist_filepath, encoding="utf-8") as classlist_file:

                classlist_dict = json.load(classlist_file)
                jsonschema.validate(instance=classlist_dict, schema=json_schema)

                for class_name, class_dict in classlist_dict["classes"].items():
                    new_class = Class(class_name)

                    class_members = class_dict["members"]
                    for class_member in class_members:
                        student = Member(class_member["name"], class_member["surname"], class_member["github_username"],
                                         class_member.get("active", True))
                        new_class.append_member(student)

                    class_moderators = class_dict["moderators"]
                    for class_moderator in class_moderators:
                        moderator = Moderator(class_moderator["name"], class_moderator["surname"],
                                              class_moderator["github_username"], class_moderator.get("active", True))
                        new_class.append_moderator(moderator)

                    self.classes_by_name[class_name] = new_class

    def get_class(self, name: str) -> Class:
        return self.classes_by_name[name]

    def get_available_class_names(self) -> List[str]:
        return list(self.classes_by_name.keys())
