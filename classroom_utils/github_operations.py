# Copyright (C) 2024 twyleg
import json
import os
import argparse
import logging
import sys
import urllib.request
from pathlib import Path

import github
import github.NamedUser
import github.GithubException
import github.Organization
import github.Repository
import github.Branch
import github.PullRequest

import git
from github.Organization import Organization
from github.PaginatedList import PaginatedList

from alive_progress import alive_bar

from typing import List

from classroom_utils.roles import GithubUser, get_class_by_name, find_personal_repo, generate_personal_repo_name, Member


class GithubCredentialsNotFoundError(Exception):
    pass


class GithubCredentials:
    GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME = "GITHUB_TOKEN"
    GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME = "GITHUB_USERNAME"

    @classmethod
    def read_github_token(cls, args: argparse.Namespace) -> str | None:
        if args.github_token:
            logging.debug("GitHub token provided via cli argument.")
            return args.github_token
        elif cls.GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME in os.environ:
            logging.debug(f"GitHub token provided via env variable {cls.GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME}.")
            return os.environ[cls.GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME]

        raise GithubCredentialsNotFoundError(f"Unable to find github token, please provide with "
                                             f"'-g/--github-token' or env variable "
                                             f"'{cls.GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME}'")

    @classmethod
    def read_github_username(cls, args: argparse.Namespace) -> str | None:
        if args.github_username:
            logging.debug("GitHub username provided via cli argument.")
            return args.github_username
        elif cls.GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME in os.environ:
            logging.debug(f"GitHub username provided via env variable {cls.GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME}.")
            return os.environ[cls.GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME]

        raise GithubCredentialsNotFoundError(f"Unable to find github username, please provide with "
                                             f"'-u/--github-username' or env variable "
                                             f"'{cls.GITHUB_USERNAME_ENVIRONMENT_VARIABLE_NAME}'")


    @classmethod
    def read_github_credentials(cls, args: argparse.Namespace) -> "GithubCredentials":
        username = cls.read_github_username(args)
        token = cls.read_github_token(args)
        return GithubCredentials(username, token)

    def __init__(self, username: str, token: str):
        self.username: str | None = username
        self.token: str | None = token

    def __bool__(self) -> bool:
        return bool(self.username) and bool(self.token)


class GithubOperations:

    def __init__(self, github_credentials: GithubCredentials):
        self.github_credentials = github_credentials
        self.github_connection = github.Github(auth=github.Auth.Token(self.github_credentials.token))

    def _validate_user(self, github_username: str) -> bool:
        try:
            self.github_connection.get_user(github_username)
            return True
        except github.UnknownObjectException as e:
            return False

    def validate_users(self, users: List[GithubUser]) -> None:

        valid_users: List[GithubUser] = []
        invalid_users: List[GithubUser] = []

        for user in users:
            valid_users.append(user) if self._validate_user(user.github_username) else invalid_users.append(user)

        logging.info("Valid:")
        for valid_user in valid_users:
            logging.info("  %s", valid_user)
        logging.info("Invalid:")
        for invalid_user in invalid_users:
            logging.info("  %s", invalid_user)

    def get_user(self) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user()

    def get_named_user(self, github_username: str) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user(github_username)

    def get_org(self, org_name: str) -> github.Organization.Organization:
        return self.github_connection.get_organization(org_name)

    def get_orgs(self) -> PaginatedList[Organization]:
        return self.get_user().get_orgs()

    def get_org_names(self) -> List[str]:
        req = urllib.request.Request(url="https://api.github.com/user/orgs", method="GET")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Authorization", f"Bearer {self.github_credentials.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        with urllib.request.urlopen(req) as res:
            data = res.read()
            data_dict = json.loads(data)
            org_names = [org["login"] for org in data_dict]
            org_names.sort()
            return org_names

    def get_full_repo_names_by_org(self, org_name: str) -> List[str]:
        org = self.get_org(org_name)
        repos = org.get_repos(sort="full_name")
        return [repo.full_name for repo in repos]

    def get_repo(self, full_repo_name: str) -> github.Repository.Repository:
        return self.github_connection.get_repo(full_repo_name)

    @staticmethod
    def get_branch_by_name(repo: github.Repository.Repository, name: str) -> github.Branch.Branch | None:
        for branch in repo.get_branches():
            if branch.name == name:
                return branch
        return None

    @staticmethod
    def get_pull_request_by_title(repo: github.Repository.Repository, title: str) -> github.PullRequest.PullRequest | None:
        for pull in repo.get_pulls():
            if pull.title == title:
                return pull
        return None

    @staticmethod
    def remove_invitation(repo: github.Repository.Repository, invitee: github.NamedUser.NamedUser) -> None:
        logging.debug("Removing invitations in repo '%s' for user '%s'", repo.full_name, invitee.login)
        for invitation in repo.get_pending_invitations():
            logging.debug("  - Found invitation: '%s'", invitation.invitee.login)
            if invitation.invitee.login == invitee.login:
                logging.debug("  - Remove invitation!")
                repo.remove_invitation(invitation.id)

    def clone_repo(self, clone_url: str, target_dir) -> None:

        logging.debug("Clone URL: '%s'", clone_url)

        os.environ["GIT_USERNAME"] = self.github_credentials.username
        os.environ["GIT_PASSWORD"] = self.github_credentials.token
        git.Repo.clone_from(clone_url, target_dir)

    def class_check(self, class_name: str) -> None:
        logging.info("Validating class '%s'", class_name)

        class_to_validate = get_class_by_name(class_name)
        logging.info("Moderators:")
        self.validate_users(class_to_validate.moderators)
        logging.info("Members:")
        self.validate_users(class_to_validate.members)

    def create_personal_class_repos_in_org(self, org_name: str, class_name: str, repo_prefix: str, template_repo_full_name: str) -> None:
        logging.info("Create class repos in org '%s' for class '%s'", org_name, class_name)

        selected_class = get_class_by_name(class_name)
        org = self.get_org(org_name)

        template_repo: github.Repository.Repository | None = None
        if template_repo_full_name:
            template_repo = self.get_repo(template_repo_full_name)
            if not template_repo.is_template:
                logging.error("Repo '%s' is not a template! Unable to create personal class repos!", template_repo.name)
                sys.exit(-1)

        for class_member in selected_class.active_members:
            repo_name = generate_personal_repo_name(class_member, repo_prefix)
            if template_repo:
                org.create_repo_from_template(repo_name, template_repo, private=True)
                logging.info("Created personal class repo '%s' from template '%s'", repo_name, template_repo.full_name)
            else:
                org.create_repo(repo_name, private=True, auto_init=True)
                logging.info("Created personal class repo '%s'", repo_name)

        for class_member in selected_class.inactive_members:
            logging.info("Skipping repo creation of '%s' due to inactivity of class member", class_member.fullname)

    def create_reviews_for_repos_in_org(self, org_name: str, class_name: str, head_branch_name: str, review_branch_name: str) -> None:

        logging.info("Create reviews in '%s' for class '%s'", org_name, class_name)

        selected_class = get_class_by_name(class_name)

        org = self.get_org(org_name)
        repos = org.get_repos()

        pr_title = "Review"

        for class_member in selected_class.active_members:

            logging.info("Class member: '%s'", class_member)

            repo = find_personal_repo(class_member, repos)

            if repo is None:
                logging.warning("Failed to create review for '%s' ('%s')! Unable to find repo in org '%s'",
                                class_member.fullname, class_member.github_username, org_name)
                continue

            logging.info("Repo: '%s'", repo.full_name)

            if self.get_branch_by_name(repo, review_branch_name) is None:
                commit_history = repo.get_commits().reversed
                first_commit = commit_history[0]

                repo.create_git_ref(f'refs/heads/{review_branch_name}', first_commit.sha)
                logging.info("Created '%s' branch from first commit ('%s')", review_branch_name, first_commit)
            else:
                logging.warning("Branch '%s' already existing in repo '%s'!", review_branch_name, repo.name)

            if self.get_pull_request_by_title(repo, pr_title) is not None:
                logging.warning("Pull-Request with '%s' already existing in repo '%s'!", review_branch_name, repo.name)
                continue

            base_branch = self.get_branch_by_name(repo, review_branch_name)
            head_branch = self.get_branch_by_name(repo, head_branch_name)

            if base_branch.commit.sha == head_branch.commit.sha:
                logging.warning("Unable to create PR! Base branch '%s' and head branch '%s' are equal.",
                                base_branch.name, head_branch.name)
                continue

            try:
                repo.create_pull(review_branch_name, head_branch_name, title=pr_title)
                logging.info("Created pullrequest '%s' <- '%s' in repository '%s'", review_branch_name,
                             head_branch_name, repo.name)
            except github.GithubException as e:
                logging.error("Create pullrequest failed with message: '$s'", e.message)

    def grant_access_to_personal_class_repos_in_org(self, org_name: str, selected_class_members: List[Member],
                                                    permission: str) -> None:
        logging.info("Grant access to personal class repos in org '%s' for the following class members:", org_name)

        org = self.get_org(org_name)

        with alive_bar(len(selected_class_members), title="Granting access:") as bar:
            for class_member in selected_class_members:
                repo_name = generate_personal_repo_name(class_member, "")

                class_member_named_user = self.get_named_user(class_member.github_username)

                repo = org.get_repo(repo_name)
                repo.add_to_collaborators(class_member_named_user, permission=permission)
                logging.info("Granted access to personal class repo for '%s' -> '%s, permission: '%s'", class_member, repo_name,
                             permission)
                bar()

    def revoke_access_from_personal_class_repos_in_org(self, org_name: str, selected_class_members: List[Member],) -> None:
        logging.info("Revoke access from personal class repos in org '%s' for the following class members:'", org_name)

        org = self.get_org(org_name)

        with alive_bar(len(selected_class_members), title="Revoking access:") as bar:
            for class_member in selected_class_members:
                repo_name = generate_personal_repo_name(class_member, "")
                class_member_named_user = self.get_named_user(class_member.github_username)
                try:
                    repo = org.get_repo(repo_name)
                    repo.remove_from_collaborators(class_member_named_user)

                    self.remove_invitation(repo, class_member_named_user)

                    logging.info("Revoked access from personal class repo '%s' for '%s'", repo.full_name, class_member)
                except github.UnknownObjectException as e:
                    logging.error("%s", e)
                    logging.error("Unable to revoke access for '%s'", repo_name)
                bar()

    def grant_class_access_to_repo(self, full_repo_name: str, selected_class_members: List[Member], permission: str) -> None:
        logging.info("Grant class access to repo '%s' with permission '%s' for the following class members:",
                     full_repo_name, permission)

        repo = self.get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Granting access:") as bar:
            for class_member in selected_class_members:
                class_member_named_user = self.get_named_user(class_member.github_username)
                logging.info("Inviting class member '%s' to repo '%s' with permission: '%s'", class_member, repo.full_name, permission)
                repo.add_to_collaborators(class_member_named_user, permission=permission)
                logging.info("Invited successfully!")
                bar()

    def revoke_class_access_from_repo(self, full_repo_name: str, selected_class_members: List[Member],) -> None:
        logging.info("Revoke class access from repo '%s' for the following class members.", full_repo_name)

        repo = self.get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Revoke access:") as bar:
            for class_member in selected_class_members:
                class_member_named_user = self.get_named_user(class_member.github_username)
                try:
                    repo.remove_from_collaborators(class_member_named_user)
                    self.remove_invitation(repo, class_member_named_user)

                    logging.info("Revoked access from repo '%s' for user '%s'", repo.full_name, class_member)
                except github.UnknownObjectException as e:
                    logging.error("%s", e)
                    logging.error("Unable to revoke access from repo '%s' for user '%s'", repo.full_name, class_member)
                bar()

    def clone_org(self, org_name: str) -> None:
        logging.info("Cloning all repos of org '%s'", org_name)

        backup_dir = Path.cwd() / org_name
        backup_dir.mkdir(exist_ok=False)

        org = self.get_org(org_name)
        repos = org.get_repos()

        with alive_bar(repos.totalCount, title="Cloning repos:") as bar:
            for repo in repos:
                backup_repo_dir = backup_dir / repo.name
                logging.info("Cloning repo '%s' -> '%s'", repo.clone_url, backup_repo_dir)
                backup_repo_dir.mkdir()
                self.clone_repo(repo.clone_url, backup_repo_dir)
                bar()

    def repo_print_details(self, full_repo_name: str) -> None:
        repo = self.get_repo(full_repo_name)

        logging.info("Repository details '%s':", full_repo_name)
        logging.info("  - Created: %s", repo.created_at)
        logging.info("  - Modified: %s", repo.last_modified)

        logging.info("  - Pending invitations:")
        invitations = repo.get_pending_invitations()
        for invitation in invitations:
            logging.info("    - %s: %s", invitation.invitee.login, invitation.permissions)

        logging.info("  - Collaborators:")
        collaborators = repo.get_collaborators()
        for collaborator in collaborators:
            collaborator_permission = repo.get_collaborator_permission(collaborator)
            logging.info("    - %s: %s", collaborator.login, collaborator_permission)

