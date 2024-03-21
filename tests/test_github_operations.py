# Copyright (C) 2023 twyleg
import pytest
import tempfile
import logging

from pathlib import Path

from classroom_utils.classes import Member

#
# General naming convention for unit tests:
#               test_INITIALSTATE_ACTION_EXPECTATION
#


class TestGithubOperations:

    def test_ArrangedState_Action_Assertion(self, caplog, tmp_path):
        test_member = Member(name="Müllerß Ölsen", surname="Rüdigör Björn", github_username="void", active=True)

        repo_name = test_member.generate_personal_repo_name()
        assert repo_name == "muellersz_oelsen_ruedigoer_bjoern"


