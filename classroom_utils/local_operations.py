# Copyright (C) 2024 twyleg
import logging

from pathlib import Path
from typing import List

from classroom_utils.roles import get_class_by_name, generate_personal_repo_name


def create_directory_structure_for_class(class_name: str, working_dir: Path, subdirs: List[str]) -> None:
    logging.debug("mkdir: %s", class_name)

    selected_class = get_class_by_name(class_name)

    for class_member in selected_class.active_members:
        repo_name = generate_personal_repo_name(class_member)

        class_member_directory_path = working_dir / repo_name

        class_member_directory_path.mkdir(parents=True, exist_ok=True)

        for subdir in subdirs:
            class_member_subdir_directory_path = class_member_directory_path / subdir
            class_member_subdir_directory_path.mkdir(parents=True, exist_ok=True)
