# Copyright (C) 2023 twyleg
import pytest
import tempfile
import logging

from pathlib import Path

from classroom_utils.roles import Member, generate_personal_repo_name

#
# General naming convention for unit tests:
#               test_INITIALSTATE_ACTION_EXPECTATION
#


class TestGithubOperations:

    def test_ArrangedState_Action_Assertion(self, caplog, tmp_path):
        test_member = Member(name="Müllerß", surname="Rüdigör", github_username="void", active=True)

        repo_name = generate_personal_repo_name(test_member)
        assert repo_name == "muellersz_ruedigoer"


