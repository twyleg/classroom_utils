# Copyright (C) 2024 twyleg
import logging

from pathlib import Path
from typing import List

from classroom_utils.classes import Class


logm = logging.getLogger("local_operations")


def create_directory_structure_for_class(selected_class: Class, working_dir: Path, subdirs: List[str]) -> None:
    logm.debug("mkdir: %s", selected_class.name)

    for class_member in selected_class.active_members:
        repo_name = class_member.generate_personal_repo_name()

        class_member_directory_path = working_dir / repo_name

        class_member_directory_path.mkdir(parents=True, exist_ok=True)

        for subdir in subdirs:
            class_member_subdir_directory_path = class_member_directory_path / subdir
            class_member_subdir_directory_path.mkdir(parents=True, exist_ok=True)
