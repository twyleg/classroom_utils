# Copyright (C) 2024 twyleg
import logging
import sys
from typing import List

from classroom_utils import github_operations
from roles import read_classes_from_config


def print_numerized_dialog(title: str, choices: List[str]) -> str:
    print(f"{title}:")
    num = 1
    for choice in choices:
        print(f"  {num}: {choice}")
        num += 1

    print("Number: ", end="")
    sys.stdout.flush()
    number = int(sys.stdin.readline())
    return choices[number-1]


def user_input_request_class_name() -> str:
    available_classes = [class_name for class_name in read_classes_from_config().keys()]
    return print_numerized_dialog("Please chose a class", available_classes)


def user_input_request_org_name(github_ops: github_operations.GithubOperations) -> str:
    available_orgs = github_ops.get_org_names()
    logging.debug("Available orgs: %s",available_orgs)
    return print_numerized_dialog("Please chose an org", available_orgs)


def user_input_request_repo_permission() -> str:
    return print_numerized_dialog("Please chose a permission", ["pull", "push"])