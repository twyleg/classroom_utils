# Copyright (C) 2024 twyleg
import argparse
import logging
import sys
from pathlib import Path
from typing import List

from classroom_utils import dialogs, github_operations, local_operations
from classroom_utils.subcommands import Command


class ClassroomUtilsBaseCommand(Command):

    def __init__(self, parser):
        super().__init__(parser)

    def get_class_name(self, args: argparse.Namespace) -> str:
        return args.class_name if args.class_name else dialogs.user_input_request_class_name()


class LocalSubCommand(ClassroomUtilsBaseCommand):

    def __init__(self, parser):
        super().__init__(parser)

        self.parser.add_argument(
            "-c",
            "--working-dir",
            help=f"Working directory (Default: ./)",
            type=str,
            default=Path.cwd()
        )


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

        class_name = self.get_class_name(args)
        working_dir = args.working_dir
        subdirs: List[str] = args.subdirs.split(",") if args.subdirs else []

        logging.info("Creating directory structure: class_name='%s', working_dir='%s', subdirs='%s'", class_name, working_dir, subdirs)
        local_operations.create_directory_structure_for_class(class_name, working_dir, subdirs)


class GithubSubCommand(ClassroomUtilsBaseCommand):

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

        self.github_credentials: None | github_operations.GithubCredentials = None
        self.github_ops: None | github_operations.GithubOperations = None

    def get_github_credentials(self, args: argparse.Namespace) -> github_operations.GithubCredentials:

        def get_printable_token(token: str) -> str:
            return f"{(len(token) - 4) * '*'}{token[-4:]}"

        github_credentials = github_operations.GithubCredentials.read_github_credentials(args)
        logging.debug("GITHUB_USER = '%s'", github_credentials.username)
        logging.debug("GITHUB_TOKEN = '%s'", get_printable_token(github_credentials.token))
        if github_credentials:
            return github_credentials
        else:
            sys.exit(-1)

    def prepare_handler(self, args: argparse.Namespace) -> None:
        self.github_credentials = self.get_github_credentials(args)
        self.github_ops = github_operations.GithubOperations(self.github_credentials)

    def get_org_name(self, args: argparse.Namespace) -> str:
        return args.org_name if args.org_name else dialogs.user_input_request_org_name(self.github_ops)

    def get_permission(self, args: argparse.Namespace) -> str:
        return args.permission if args.permission else dialogs.user_input_request_repo_permission()

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        logging.info("github:")


class GithubCheckClassSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        class_name = self.get_class_name(args)

        logging.info("github check class:")
        logging.info("\tclass_name=%s", class_name)


class GithubOrgSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--org-name', type=str, default=None, help="Org name")

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info("github org:")
        logging.info("\torg_name=%s", org_name)


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
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        class_name = self.get_class_name(args)
        repo_prefix = args.repo_prefix
        template = args.template

        logging.info(f"github org init:")
        logging.info("\torg_name=%s", org_name)
        logging.info("\tclass_name=%s", class_name)
        logging.info("\trepo_prefix=%s", repo_prefix)
        logging.info("\ttemplate=%s", template)


class GithubOrgAccessSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info(f"github org access:")
        logging.info("\torg_name=%s", org_name)


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
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        class_name = self.get_class_name(args)
        permission = self.get_permission(args)

        logging.info(f"github org access grant:")
        logging.info("\torg_name=%s", org_name)
        logging.info("\tclass_name=%s", class_name)
        logging.info("\tpermission=%s", permission)


class GithubOrgAccessRevokeSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info(f"github org access grant:")
        logging.info("\torg_name=%s", org_name)


class GithubOrgReviewCreateSubCommand(GithubOrgSubCommand):
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
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        head_branch_name = args.head_branch
        review_branch = args.review_branch

        logging.info(f"github org review create:")
        logging.info("\torg_name=%s", org_name)
        logging.info("\thead_branch=%s", head_branch_name)
        logging.info("\treview_branch=%s", review_branch)


class GithubOrgReviewStatusSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info(f"github org review status:")
        logging.info("\torg_name=%s", org_name)