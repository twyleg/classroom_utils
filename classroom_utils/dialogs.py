# Copyright (C) 2024 twyleg
import logging
from typing import List

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from classroom_utils import github_operations
from classroom_utils.classes import Member


logm = logging.getLogger("dialogs")


def user_input_request_class_name(available_classes: List[str]) -> str:
    available_classes = [class_name for class_name in available_classes]
    logm.debug("Available classes: %s", available_classes)
    return inquirer.fuzzy(
        message="Select a class:",
        choices=available_classes,
        border=True
    ).execute()


def user_input_request_org_name(github_ops: github_operations.GithubOperations) -> str:
    available_orgs = github_ops.get_org_names()
    logm.debug("Available orgs: %s",available_orgs)
    return inquirer.fuzzy(
        message="Select an org:",
        choices=available_orgs,
        border=True
    ).execute()


def user_input_request_repo_name(github_ops: github_operations.GithubOperations) -> str:
    org_name = user_input_request_org_name(github_ops)
    full_repo_names_of_org = github_ops.get_full_repo_names_by_org(org_name)
    logm.debug("Available repos in org '%s': %s",org_name, full_repo_names_of_org)
    return inquirer.fuzzy(
        message="Select a repo:",
        choices=full_repo_names_of_org,
        border=True
    ).execute()


def user_input_request_repo_permission() -> str:
    return inquirer.select(
        message="Choose a permission:",
        choices=["pull", "push"],
        border=True
    ).execute()


def user_input_request_selected_class_members(class_members: List[Member]) -> List[Member]:
    choices = [Choice(class_member.fullname, enabled=True) for class_member in class_members]
    result = inquirer.checkbox(
        message="Select members of class (Toggle: <SPACE>, Toggle-All: <Ctrl+r>):",
        choices=choices,
        cycle=False,
    ).execute()

    selected_class_members: List[Member] = []
    for class_member in class_members:
        if class_member.fullname in result:
            selected_class_members.append(class_member)

    return selected_class_members


def user_input_request_optional_repo_prefix() -> str | None:
    yes = inquirer.confirm(message="Specify repo prefix?", default=False).execute()

    if not yes:
        return None

    prefix = inquirer.text(
        message="Repo prefix to use:",
        multicolumn_complete=True,
    ).execute()

    return prefix.rstrip("_")


def user_input_request_optional_template_repo_name(github_ops: github_operations.GithubOperations) -> str | None:
    yes = inquirer.confirm(message="Specify repo template?", default=False).execute()

    if not yes:
        return None

    available_orgs = github_ops.get_org_names()
    logm.debug("Available orgs: %s",available_orgs)
    org_name = inquirer.fuzzy(
        message="Select org of template:",
        choices=available_orgs,
        border=True
    ).execute()

    full_repo_names_of_org = github_ops.get_full_repo_names_by_org(org_name)
    logm.debug("Choose repos in org '%s': %s",org_name, full_repo_names_of_org)
    return inquirer.fuzzy(
        message="Select a template repo:",
        choices=full_repo_names_of_org,
        border=True
    ).execute()

def user_input_request_head_branch_name() -> str | None:
    return inquirer.text(
        message="Head branch name:",
        multicolumn_complete=True,
    ).execute()

def user_input_request_review_branch_name() -> str | None:
    return inquirer.text(
        message="Review branch name:",
        multicolumn_complete=True,
    ).execute()

