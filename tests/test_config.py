# Copyright (C) 2023 twyleg
import pytest
import tempfile
import logging

from pathlib import Path

from classroom_utils.config import Config
from classroom_utils.roles import Member, generate_personal_repo_name

#
# General naming convention for unit tests:
#               test_INITIALSTATE_ACTION_EXPECTATION
#


class TestGithubOperations:

    def prepare_valid_config(self, tmp_dir_path: Path) -> Path:
        config_filepath = tmp_dir_path / "config.json"
        with open(config_filepath, "w+") as config_file:
            config_file.write(r"""{
                "github_token": "token_xxx",
                "github_username": "user",
                "class_lists": [
                    "relative_to_config_subfolder\\class_list_a.json",
                    "C:\\Users\\USERNAME\\absolute_path\\class_list_b.json"
                ]
            }
            """)
        return config_filepath

    def test_ArrangedState_Action_Assertion(self, caplog, tmp_path):
        config_filepath = self.prepare_valid_config(tmp_path)

        print(config_filepath)

        config = Config()
        config.read_from_file(config_filepath)
        assert config.github_token == "token_xxx"
        assert config.github_username == "user"
        assert config.classlist_filepaths[0] == config_filepath.parent / "relative_to_config_subfolder\\class_list_a.json"
        assert config.classlist_filepaths[1] == Path("C:\\Users\\USERNAME\\absolute_path\\class_list_b.json")


