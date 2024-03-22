# Copyright (C) 2024 twyleg
import json
import os
import logging
import sys
import urllib.request
import git

import github
import github.NamedUser
import github.GithubException
import github.Organization
import github.Repository
import github.Branch
import github.PullRequest

from typing import List, NamedTuple
from pathlib import Path
from requests.models import PreparedRequest

from github.Organization import Organization
from github.PaginatedList import PaginatedList
from alive_progress import alive_bar

from classroom_utils.classes import User, Classes, Member


logm = logging.getLogger("github_operations")


class GithubCredentials(NamedTuple):
    username: str
    token: str


class GithubOperations:

    def __init__(self, classes: Classes, github_credentials: GithubCredentials):
        self.classes = classes
        self.github_credentials = github_credentials
        self.github_connection = github.Github(auth=github.Auth.Token(self.github_credentials.token))

    def _validate_user(self, github_username: str) -> bool:
        try:
            self.github_connection.get_user(github_username)
            return True
        except github.UnknownObjectException as e:
            return False

    def validate_users(self, users: List[User]) -> None:
        with alive_bar(len(users), title="Validating users:", enrich_print=False) as bar:
            for user in users:
                if self._validate_user(user.github_username):
                    logm.info("  Valid: %s", user)
                else:
                    logm.warning("  Invalid: %s", user)
                bar()

    def get_user(self) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user()

    def get_named_user(self, github_username: str) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user(github_username)

    def get_org(self, org_name: str) -> github.Organization.Organization:
        return self.github_connection.get_organization(org_name)

    def get_orgs(self) -> PaginatedList[Organization]:
        return self.get_user().get_orgs()

    def get_org_names(self) -> List[str]:

        org_names: List[str] = []

        params = {
            "per_page": "100",
            "sort": "full_name",
            "page": 1
        }

        while True:
            url = "https://api.github.com/user/orgs"

            req_prep = PreparedRequest()
            req_prep.prepare_url(url, params)

            params["page"] += 1

            req = urllib.request.Request(url=req_prep.url, method="GET")

            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("Authorization", f"Bearer {self.github_credentials.token}")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            with urllib.request.urlopen(req) as res:
                data = res.read()
                data_dict = json.loads(data)

                for org in data_dict:
                    org_names.append(org["login"])
            if len(data_dict) == 0:
                return org_names

    def get_repo_names_by_org(self, org_name: str) -> List[str]:
        org = self.get_org(org_name)
        repos = org.get_repos(sort="name")
        return [repo.name for repo in repos]

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
        logm.debug("Removing invitations in repo '%s' for user '%s'", repo.full_name, invitee.login)

        pending_invitations = repo.get_pending_invitations()

        with alive_bar(pending_invitations.totalCount, title="Granting access:", enrich_print=False) as bar:
            for invitation in pending_invitations:
                logm.debug("  - Found invitation: '%s'", invitation.invitee.login)
                if invitation.invitee.login == invitee.login:
                    logm.debug("  - Remove invitation!")
                    repo.remove_invitation(invitation.id)
            bar()

    def clone_repo(self, clone_url: str, target_dir) -> None:

        logm.debug("Clone URL: '%s'", clone_url)

        os.environ["GIT_USERNAME"] = self.github_credentials.username
        os.environ["GIT_PASSWORD"] = self.github_credentials.token
        git.Repo.clone_from(clone_url, target_dir)

    def get_user_info(self, github_username: str) -> None:
        github_user = self.get_named_user(github_username)
        logm.info("Name: %s", github_user.name)
        logm.info("GitHub username: %s", github_user.login)
        logm.info("Orgs:")
        for org_name in self.get_org_names():
            logm.info("  %s", org_name)

    def class_check(self, class_name: str) -> None:
        logm.info("Validating class '%s'", class_name)

        class_to_validate = self.classes.get_class(class_name)
        logm.info("Moderators:")
        self.validate_users(class_to_validate.moderators)
        logm.info("Members:")
        self.validate_users(class_to_validate.members)

    def create_personal_class_repos_in_org(self, org_name: str, class_name: str, repo_prefix: str | None, template_repo_full_name: str | None) -> None:
        logm.info("Create class repos in org '%s' for class '%s'", org_name, class_name)

        selected_class = self.classes.get_class(class_name)
        org = self.get_org(org_name)

        template_repo: github.Repository.Repository | None = None
        if template_repo_full_name:
            template_repo = self.get_repo(template_repo_full_name)
            if not template_repo.is_template:
                logm.error("Repo '%s' is not a template! Unable to create personal class repos!", template_repo.name)
                sys.exit(-1)

        with alive_bar(len(selected_class.members), title="Granting access:", enrich_print=False) as bar:
            for class_member in selected_class.active_members:
                repo_name = class_member.generate_personal_repo_name(repo_prefix)
                if template_repo:
                    org.create_repo_from_template(repo_name, template_repo, private=True)
                    logm.info("Created personal class repo '%s' from template '%s'", repo_name, template_repo.full_name)
                else:
                    org.create_repo(repo_name, private=True, auto_init=True)
                    logm.info("Created personal class repo '%s'", repo_name)
                bar()

            for class_member in selected_class.inactive_members:
                logm.info("Skipping repo creation of '%s' due to inactivity of class member", class_member.fullname)
                bar()

    def create_reviews_for_repos_in_org(self, org_name: str, class_name: str, head_branch_name: str, review_branch_name: str) -> None:

        logm.info("Create reviews in '%s' for class '%s'", org_name, class_name)

        selected_class = self.classes.get_class(class_name)

        org = self.get_org(org_name)
        repos = org.get_repos()

        pr_title = "Review"

        active_members = list(selected_class.active_members)

        with alive_bar(len(active_members), title="Cloning repos:", enrich_print=False) as bar:
            for class_member in active_members:

                logm.info("Class member: '%s'", class_member)

                repo = class_member.find_personal_repo(repos)

                if repo is None:
                    logm.warning("Failed to create review for '%s' ('%s')! Unable to find repo in org '%s'",
                                 class_member.fullname, class_member.github_username, org_name)
                    continue

                logm.info("Repo: '%s'", repo.full_name)

                if self.get_branch_by_name(repo, review_branch_name) is None:
                    commit_history = repo.get_commits().reversed
                    first_commit = commit_history[0]

                    repo.create_git_ref(f'refs/heads/{review_branch_name}', first_commit.sha)
                    logm.info("Created '%s' branch from first commit ('%s')", review_branch_name, first_commit)
                else:
                    logm.warning("Branch '%s' already existing in repo '%s'!", review_branch_name, repo.name)

                if self.get_pull_request_by_title(repo, pr_title) is not None:
                    logm.warning("Pull-Request with '%s' already existing in repo '%s'!", review_branch_name, repo.name)
                    continue

                base_branch = self.get_branch_by_name(repo, review_branch_name)
                head_branch = self.get_branch_by_name(repo, head_branch_name)

                if base_branch.commit.sha == head_branch.commit.sha:
                    logm.warning("Unable to create PR! Base branch '%s' and head branch '%s' are equal.",
                                    base_branch.name, head_branch.name)
                    continue

                try:
                    repo.create_pull(review_branch_name, head_branch_name, title=pr_title)
                    logm.info("Created pullrequest '%s' <- '%s' in repository '%s'", review_branch_name,
                                 head_branch_name, repo.name)
                except github.GithubException as e:
                    logm.error("Create pullrequest failed with message: '$s'", e.message)
            bar()

    def grant_access_to_personal_class_repos_in_org(self, org_name: str, selected_class_members: List[Member],
                                                    permission: str) -> None:
        logm.info("Grant access to personal class repos in org '%s' for the following class members:", org_name)

        org = self.get_org(org_name)

        with alive_bar(len(selected_class_members), title="Granting access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                repo_name = class_member.generate_personal_repo_name()

                class_member_named_user = self.get_named_user(class_member.github_username)

                repo = org.get_repo(repo_name)
                repo.add_to_collaborators(class_member_named_user, permission=permission)
                logm.info("Granted access to personal class repo for '%s' -> '%s, permission: '%s'", class_member, repo_name,
                             permission)
                bar()

    def revoke_access_from_personal_class_repos_in_org(self, org_name: str, selected_class_members: List[Member],) -> None:
        logm.info("Revoke access from personal class repos in org '%s' for the following class members:'", org_name)

        org = self.get_org(org_name)

        for class_member in selected_class_members:
            repo_name = class_member.generate_personal_repo_name()
            class_member_named_user = self.get_named_user(class_member.github_username)
            try:
                repo = org.get_repo(repo_name)
                repo.remove_from_collaborators(class_member_named_user)

                self.remove_invitation(repo, class_member_named_user)

                logm.info("Revoked access from personal class repo '%s' for '%s'", repo.full_name, class_member)
            except github.UnknownObjectException as e:
                logm.error("%s", e)
                logm.error("Unable to revoke access for '%s'", repo_name)

    def grant_class_access_to_repo(self, full_repo_name: str, selected_class_members: List[Member], permission: str) -> None:
        logm.info("Grant class access to repo '%s' with permission '%s' for the following class members:",
                  full_repo_name, permission)

        repo = self.get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Granting access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                class_member_named_user = self.get_named_user(class_member.github_username)
                logm.info("Inviting class member '%s' to repo '%s' with permission: '%s'", class_member, repo.full_name, permission)
                repo.add_to_collaborators(class_member_named_user, permission=permission)
                logm.info("Invited successfully!")
                bar()

    def revoke_class_access_from_repo(self, full_repo_name: str, selected_class_members: List[Member],) -> None:
        logm.info("Revoke class access from repo '%s' for the following class members.", full_repo_name)

        repo = self.get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Revoke access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                class_member_named_user = self.get_named_user(class_member.github_username)
                try:
                    repo.remove_from_collaborators(class_member_named_user)
                    self.remove_invitation(repo, class_member_named_user)

                    logm.info("Revoked access from repo '%s' for user '%s'", repo.full_name, class_member)
                except github.UnknownObjectException as e:
                    logm.error("%s", e)
                    logm.error("Unable to revoke access from repo '%s' for user '%s'", repo.full_name, class_member)
                bar()

    def clone_org(self, org_name: str, working_dir: Path) -> None:
        logm.info("Cloning all repos of org '%s'", org_name)

        backup_dir = working_dir / org_name
        backup_dir.mkdir(exist_ok=False)

        org = self.get_org(org_name)
        repos = org.get_repos()

        with alive_bar(repos.totalCount, title="Cloning repos:", enrich_print=False) as bar:
            for repo in repos:
                backup_repo_dir = backup_dir / repo.name
                logm.info("Cloning repo '%s' -> '%s'", repo.clone_url, backup_repo_dir)
                backup_repo_dir.mkdir()
                self.clone_repo(repo.clone_url, backup_repo_dir)
                bar()

    def repo_print_details(self, full_repo_name: str) -> None:
        repo = self.get_repo(full_repo_name)

        logm.info("Repository details '%s':", full_repo_name)
        logm.info("  - Created: %s", repo.created_at)
        logm.info("  - Modified: %s", repo.last_modified)

        logm.info("  - Pending invitations:")
        invitations = repo.get_pending_invitations()
        for invitation in invitations:
            logm.info("    - %s: %s", invitation.invitee.login, invitation.permissions)

        logm.info("  - Collaborators:")
        collaborators = repo.get_collaborators()
        for collaborator in collaborators:
            collaborator_permission = repo.get_collaborator_permission(collaborator)
            logm.info("    - %s: %s", collaborator.login, collaborator_permission)
