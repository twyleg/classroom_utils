# Copyright (C) 2024 twyleg
import logging

from pathlib import Path
from typing import List


def create_directory_structure_for_class(class_name: str, working_dir: Path, subdirs: List[str]) -> None:
    logging.debug("mkdir: %s", class_name)
