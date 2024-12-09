# Copyright (C) 2024 twyleg
import argparse
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import List, Tuple, NamedTuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from classroom_utils.ascii_art import CLASSROOM_UTILS_BANNER_2
from classroom_utils import dialogs, github_operations, local_operations
from classroom_utils.classes import Classes, Member
from classroom_utils.config import Config
from classroom_utils.github_operations import GithubCredentials
from classroom_utils.subcommands import Command, RootCommand, SubcommandNotAvailableError


logm = logging.getLogger("cli")


class PromptRootCommand(RootCommand):

    PROMPT_STYLE = Style.from_dict(
        {
            # Default style.
            "": "#ff1618 bold",
            # Prompt.
            "prompt": "#1dcf84 italic",
        }
    )

    PROMPT_FRAGMENTS = [
        ("class:prompt", "classroom_utils $ "),
    ]

    def __init__(self):
        super().__init__()

    def handle(self, args: argparse.Namespace) -> None:
        completer = NestedCompleter.from_nested_dict(self.commands_to_dict())
        session = PromptSession(history=InMemoryHistory(), completer=completer)

        print(CLASSROOM_UTILS_BANNER_2)

        while True:
            try:
                subcommand_string = session.prompt(self.PROMPT_FRAGMENTS, style=self.PROMPT_STYLE)
            except KeyboardInterrupt as e:
                logm.info("Exiting...")
                sys.exit(0)

            if subcommand_string:
                try:
                    logm.debug("Entered command: %s", subcommand_string)
                    subcommand = self.find_subcommand(subcommand_string)
                    subcommand.handle(args)
                except KeyboardInterrupt as e:
                    logm.info("Command aborted...")
                except SubcommandNotAvailableError as e:
                    print(f"Command unavailable: '{subcommand_string}'")
                except Exception as e:
                    logm.error("%s: %s", e.__class__.__name__, e)
                    logm.debug(traceback.format_exc())


class ClassroomUtilsBaseCommand(Command):

    def __init__(self, parser):
        super().__init__(parser)
        self.config = Config()
        self.classes = Classes()

        self.parser.add_argument(
            "-c",
            "--config",
            help=f"Config file to use.",
            type=str,
            default=None
        )

    def prepare_handler(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)

        if hasattr(args, "config") and args.config:
            logm.info("Config file provided via argument: %s", args.config)
            self.config.read_from_file(Path(args.config))
        else:
            config_filepath = Config.find_config_filepath()
            self.config.read_from_file(config_filepath)

        for classlist_filepath in self.config.classlist_filepaths:
            self.classes.read_classlist_from_file(classlist_filepath)

    def get_class_name_from_user(self, args: argparse.Namespace) -> str:
        return args.class_name if hasattr(args, "class_name") and args.class_name else dialogs.user_input_request_class_name(self.classes.get_available_class_names())

    def get_selected_class_members_from_user(self, class_name: str) -> List[Member]:
        class_members = self.classes.get_class(class_name)
        return dialogs.user_input_request_selected_class_members(list(class_members.active_members))


class LocalSubCommand(ClassroomUtilsBaseCommand):

    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "--working-dir",
            help=f"Working directory (Default: ./)",
            type=str,
            default=Path.cwd()
        )

    def prepare_handler(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)


class LocalClassMkdirSubCommand(LocalSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")
        self.parser.add_argument(
            "--subdirs",
            help=f"Comma seperated list of subdirectories to create in every member directory",
            type=str,
            default=None
        )

    def handle(self, args: argparse.Namespace) -> None:
        print(f"local class mkdir")

        class_name = self.get_class_name_from_user(args)
        selected_class = self.classes.get_class(class_name)
        working_dir = Path(args.working_dir)
        subdirs: List[str] = args.subdirs.split(",") if args.subdirs else []

        logm.info("Creating directory structure: class_name='%s', working_dir='%s', subdirs='%s'", class_name, working_dir, subdirs)
        local_operations.create_directory_structure_for_class(selected_class, working_dir, subdirs)


class GithubCredentialsNotFoundError(Exception):
    pass


class GithubSubCommand(ClassroomUtilsBaseCommand):

    GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME = "GITHUB_TOKEN"
    GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME = "GITHUB_USERNAME"

    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "-g",
            "--github-token",
            help="GitHub token to use. Otherwise env variable GITHUB_TOKEN is used.",
            default=None
        )

        self.parser.add_argument(
            "-u",
            "--github-username",
            help="GitHub username to use. Otherwise env variable GITHUB_USERNAME is used.",
            default=None
        )

        self.github_ops: None | github_operations.GithubOperations = None

    def prepare_handler(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        try:
            github_credentials = self.get_github_credentials(args)
            self.github_ops = github_operations.GithubOperations(self.classes, github_credentials)
        except GithubCredentialsNotFoundError as e:
            logm.error(e)
            sys.exit(-1)

    def read_github_token(self, args: argparse.Namespace) -> str:
        if hasattr(args, "github_token") and args.github_token:
            logm.debug("Using GitHub token provided via cli argument.")
            return args.github_token

        logm.debug(f"Using GitHub token from config.")
        return self.config.github_token

    def read_github_username(self, args: argparse.Namespace) -> str:
        if hasattr(args, "github_username") and args.github_username:
            logm.debug("Using GitHub username provided via cli argument.")
            return args.github_username

        logm.debug("Using GitHub username from config.")
        return self.config.github_username

    @classmethod
    def get_printable_token(cls, token: str) -> str:
        return f"{(len(token) - 4) * '*'}{token[-4:]}"

    def get_github_credentials(self, args: argparse.Namespace) -> GithubCredentials:

        github_username = self.read_github_username(args)
        github_token = self.read_github_token(args)

        logm.debug("GITHUB_USER = '%s'", github_username)
        logm.debug("GITHUB_TOKEN = '%s'", self.get_printable_token(github_token))

        return GithubCredentials(github_username, github_token)

    def get_repo_prefix_from_user(self, args: argparse.Namespace) -> str | None:
        return args.repo_prefix if hasattr(args, "repo_prefix") and args.repo_prefix else dialogs.user_input_request_optional_repo_prefix()

    def get_template_from_user(self, args: argparse.Namespace) -> str | None:
        return args.template if hasattr(args, "template") and args.template else dialogs.user_input_request_optional_template_repo_name(self.github_ops)

    def get_org_name_from_user(self, args: argparse.Namespace) -> str:
        return args.org_name if hasattr(args, "org_name") and args.org_name else dialogs.user_input_request_org_name(self.github_ops)

    def get_repo_name_from_user(self, args: argparse.Namespace) -> str:
        return args.repo if hasattr(args, "repo") and args.repo else dialogs.user_input_request_repo_name(self.github_ops)

    def get_permission_from_user(self, args: argparse.Namespace) -> str:
        return args.permission if hasattr(args, "permission") and args.permission else dialogs.user_input_request_repo_permission()

    def get_head_branch_name_from_user(self, args: argparse.Namespace) -> str:
        return args.permission if hasattr(args, "head_branch") and args.permission else dialogs.user_input_request_head_branch_name()

    def get_review_branch_name_from_user(self, args: argparse.Namespace) -> str:
        return args.permission if hasattr(args, "review_branch") and args.permission else dialogs.user_input_request_review_branch_name()

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        logm.debug("github:")

        self.github_ops.get_user_info(self.github_ops.get_user().login)


class GithubClassCheckSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        class_name = self.get_class_name_from_user(args)

        logm.debug("github check class:")
        logm.debug("\t-class_name=%s", class_name)

        self.github_ops.class_check(class_name)


class GithubOrgSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--org-name', type=str, default=None, help="Org name")

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)

        logm.debug("github org:")
        logm.debug("\t-org_name=%s", org_name)

        logm.warning("Not yet implemented!")


class GithubOrgInitSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")
        self.parser.add_argument(
            "--repo-prefix",
            help="Prefix of the created repos, eg. 'excercise_name_surname'.",
            type=str,
            default=None
        )
        self.parser.add_argument(
            "-t",
            "--template",
            help="Template project to use for personal class repos.",
            type=str,
            default=None
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        repo_prefix = self.get_repo_prefix_from_user(args)
        template = self.get_template_from_user(args)

        logm.debug(f"github org init:")
        logm.debug("\t-org_name=%s", org_name)
        logm.debug("\t-class_name=%s", class_name)
        logm.debug("\t-repo_prefix=%s", repo_prefix)
        logm.debug("\t-template=%s", template)

        self.github_ops.org_create_personal_repos(org_name, class_name, repo_prefix, template)


class GithubOrgCloneSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")
        self.parser.add_argument(
            "-w",
            "--working-dir",
            help="Working directory.",
            type=Path,
            default=Path.cwd()
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)
        working_dir = args.working_dir

        logm.debug(f"github org clone:")
        logm.debug("\t-org_name=%s", org_name)
        logm.debug("\t-working_dir=%s", working_dir)

        self.github_ops.clone_org(org_name, working_dir)


class GithubOrgAccessSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)

        logm.debug(f"github org access:")
        logm.debug("\t-org_name=%s", org_name)


class GithubOrgAccessGrantSubCommand(GithubOrgInitSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "--permission",
            help="Permisison to grant (push or pull)",
            type=str,
            choices=["push", "pull"],
            default=None
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        selected_class_members = self.get_selected_class_members_from_user(class_name)
        permission = self.get_permission_from_user(args)

        logm.debug(f"github org access grant:")
        logm.debug("\t-org_name=%s", org_name)
        logm.debug("\t-class_name=%s", class_name)
        logm.debug("\t-selected_class_members%s", selected_class_members)
        logm.debug("\t-permission=%s", permission)

        self.github_ops.org_access_grant_personal_repos(org_name, selected_class_members, permission)


class GithubOrgAccessRevokeSubCommand(GithubOrgInitSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        selected_class_members = self.get_selected_class_members_from_user(class_name)

        logm.debug(f"github org access grant:")
        logm.debug("\t-org_name=%s", org_name)
        logm.debug("\t-class_name=%s", class_name)
        logm.debug("\t-selected_class_members%s", selected_class_members)

        self.github_ops.org_access_revoke_personal_repos(org_name, selected_class_members)


class GithubOrgReviewCreateSubCommand(GithubOrgInitSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "--head-branch",
            help="Name of the branch to create the PR from.",
            type=str,
            default="master"
        )
        self.parser.add_argument(
            "--review-branch",
            help="Name of the review branch to create.",
            type=str,
            default="review"
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        head_branch_name = self.get_head_branch_name_from_user(args)
        review_branch_name = self.get_review_branch_name_from_user(args)

        logm.debug(f"github org review create:")
        logm.debug("\torg_name=%s", org_name)
        logm.debug("\tclass_name=%s", class_name)
        logm.debug("\thead_branch=%s", head_branch_name)
        logm.debug("\treview_branch=%s", review_branch_name)

        self.github_ops.org_reviews_create(org_name, class_name, head_branch_name, review_branch_name)


class GithubOrgReviewStatusSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        org_name = self.get_org_name_from_user(args)

        logm.debug(f"github org review status:")
        logm.debug("\torg_name=%s", org_name)

        logm.warning("Not yet implemented!")


class GithubRepoSubCommand(GithubSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")
        self.parser.add_argument(
            "--repo",
            help="Name of the repository.",
            type=str,
            default=None
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        repo_name = self.get_repo_name_from_user(args)

        logm.debug(f"github repo:")
        logm.debug("\t-repo_name=%s", repo_name)

        self.github_ops.repo_print_details(repo_name)


class GithubRepoAccessGrantSubCommand(GithubRepoSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "--permission",
            help="Permisison to grant (push or pull)",
            type=str,
            choices=["push", "pull"],
            default=None
        )

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        repo_name = self.get_repo_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        selected_class_members = self.get_selected_class_members_from_user(class_name)
        permission = self.get_permission_from_user(args)

        logm.debug(f"github repo access grant")
        logm.debug("\t-repo_name=%s", repo_name)
        logm.debug("\t-class_name=%s", class_name)
        logm.debug("\t-selected_class_members=%s", selected_class_members)
        logm.debug("\t-permission=%s", permission)

        self.github_ops.repo_access_grant_for_class(repo_name, selected_class_members, permission)


class GithubRepoAccessRevokeSubCommand(GithubRepoSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        repo_name = self.get_repo_name_from_user(args)
        class_name = self.get_class_name_from_user(args)
        selected_class_members = self.get_selected_class_members_from_user(class_name)

        logm.debug(f"github repo access revoke:")
        logm.debug("\t-repo_name=%s", repo_name)
        logm.debug("\t-class_name=%s", class_name)
        logm.debug("\t-selected_class_members=%s", selected_class_members)

        self.github_ops.repo_access_revoke_for_class(repo_name, selected_class_members)

