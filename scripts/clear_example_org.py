# Copyright (C) 2024 twyleg
import logging
import argparse
import sys

import github

from pathlib import Path
from classroom_utils.github_operations import GithubCredentials

FILE_DIR = Path(__file__).parent
FORMAT = "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s"

EXAMPLE_ORG_NAME = "classroom-utils-example-org"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage="clear_example_org [<args>]")
    parser.add_argument(
        "-g",
        "--github-token",
        help="GitHub token to use. Otherwise env variable GITHUB_TOKEN is used.",
        default=None
    )

    parser.add_argument(
        "-u",
        "--github-username",
        help="GitHub username to use. Otherwise env variable GITHUB_USERNAME is used.",
        default=None
    )

    parser.add_argument(
        "-vv",
        "--verbose",
        help="Run with verbose output.",
        action='store_true',
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=log_level, force=True)

    github_credentials = GithubCredentials.read_github_credentials(args)
    github_connection = github.Github(auth=github.Auth.Token(github_credentials.token))

    org = github_connection.get_organization(EXAMPLE_ORG_NAME)
    repos = org.get_repos()

    logging.info("Clearing example org: '%s'", org.name)
    for repo in repos:
        logging.info("  - %s", repo.full_name)
        repo.delete()
