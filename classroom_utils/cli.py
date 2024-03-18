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
        working_dir = Path(args.working_dir)
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

    def get_repo_name(self, args: argparse.Namespace) -> str:
        return args.repo if args.repo else dialogs.user_input_request_repo_name(self.github_ops)

    def get_permission(self, args: argparse.Namespace) -> str:
        return args.permission if args.permission else dialogs.user_input_request_repo_permission()

    def handle(self, args: argparse.Namespace) -> None:
        self.prepare_handler(args)
        logging.info("github:")


class GithubClassCheckSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--class-name', type=str, default=None, help="Class name")

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        class_name = self.get_class_name(args)

        logging.info("github check class:")
        logging.info("\t-class_name=%s", class_name)

        self.github_ops.class_check(class_name)


class GithubOrgSubCommand(GithubSubCommand):

    def __init__(self, parser):
        super().__init__(parser)
        self.parser.add_argument('--org-name', type=str, default=None, help="Org name")

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info("github org:")
        logging.info("\t-org_name=%s", org_name)


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
        logging.info("\t-org_name=%s", org_name)
        logging.info("\t-class_name=%s", class_name)
        logging.info("\t-repo_prefix=%s", repo_prefix)
        logging.info("\t-template=%s", template)

        self.github_ops.create_personal_class_repos_in_org(org_name, class_name, repo_prefix, template)


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
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        working_dir = args.working_dir


        logging.info(f"github org clone:")
        logging.info("\t-org_name=%s", org_name)
        logging.info("\t-working_dir=%s", working_dir)

        self.github_ops.clone_org(org_name, working_dir)


class GithubOrgAccessSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info(f"github org access:")
        logging.info("\t-org_name=%s", org_name)


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
        logging.info("\t-org_name=%s", org_name)
        logging.info("\t-class_name=%s", class_name)
        logging.info("\t-permission=%s", permission)

        self.github_ops.grant_access_to_personal_class_repos_in_org(org_name, class_name, permission)


class GithubOrgAccessRevokeSubCommand(GithubOrgInitSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        class_name = self.get_class_name(args)

        logging.info(f"github org access grant:")
        logging.info("\t-org_name=%s", org_name)
        logging.info("\t-class_name=%s", class_name)

        self.github_ops.revoke_access_from_personal_class_repos_in_org(org_name, class_name)


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
        super().prepare_handler(args)
        org_name = self.get_org_name(args)
        class_name = self.get_class_name(args)
        head_branch_name = args.head_branch
        review_branch_name = args.review_branch

        logging.info(f"github org review create:")
        logging.info("\torg_name=%s", org_name)
        logging.info("\tclass_name=%s", class_name)
        logging.info("\thead_branch=%s", head_branch_name)
        logging.info("\treview_branch=%s", review_branch_name)

        self.github_ops.create_reviews_for_repos_in_org(org_name, class_name, head_branch_name, review_branch_name)


class GithubOrgReviewStatusSubCommand(GithubOrgSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        org_name = self.get_org_name(args)

        logging.info(f"github org review status:")
        logging.info("\torg_name=%s", org_name)


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
        super().prepare_handler(args)
        repo_name = self.get_repo_name(args)

        logging.info(f"github org review status:")
        logging.info("\t-repo_name=%s", repo_name)

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
        super().prepare_handler(args)
        repo_name = self.get_repo_name(args)
        class_name = self.get_class_name(args)
        permission = self.get_permission(args)

        logging.info(f"github org review status:")
        logging.info("\t-repo_name=%s", repo_name)
        logging.info("\t-class_name=%s", class_name)
        logging.info("\t-permission=%s", permission)

        self.github_ops.grant_class_access_to_repo(repo_name, class_name, permission)


class GithubRepoAccessRevokeSubCommand(GithubRepoSubCommand):
    def __init__(self, parser):
        super().__init__(parser)

    def handle(self, args: argparse.Namespace) -> None:
        super().prepare_handler(args)
        repo_name = self.get_repo_name(args)
        class_name = self.get_class_name(args)

        logging.info(f"github org review status:")
        logging.info("\t-repo_name=%s", repo_name)
        logging.info("\t-class_name=%s", class_name)

        self.github_ops.revoke_class_access_from_repo(repo_name, class_name)

