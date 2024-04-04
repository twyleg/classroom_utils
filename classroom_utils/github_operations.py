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

    def _validate_users(self, users: List[User]) -> None:
        with alive_bar(len(users), title="Validating users:", enrich_print=False) as bar:
            for user in users:
                if self._validate_user(user.github_username):
                    logm.info("  Valid: %s", user)
                else:
                    logm.warning("  Invalid: %s", user)
                bar()

    def _get_named_user(self, github_username: str) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user(github_username)

    def _get_org(self, org_name: str) -> github.Organization.Organization:
        return self.github_connection.get_organization(org_name)

    def _get_orgs(self) -> PaginatedList[Organization]:
        return self.get_user().get_orgs()

    def _get_repo(self, full_repo_name: str) -> github.Repository.Repository:
        return self.github_connection.get_repo(full_repo_name)

    def _get_template_repo(self, template_repo_full_name: str) -> github.Repository.Repository:
        template_repo = self._get_repo(template_repo_full_name)
        if template_repo.is_template:
            return template_repo
        else:
            logm.error("Repo '%s' is not a template! Unable to create personal class repos!", template_repo.name)
            sys.exit(-1)

    def _is_repo_existing(self, full_repo_name: str) -> bool:
        try:
            self.github_connection.get_repo(full_repo_name)
            return True
        except github.GithubException:
            return False

    @staticmethod
    def _get_branch_by_name(repo: github.Repository.Repository, name: str) -> github.Branch.Branch | None:
        for branch in repo.get_branches():
            if branch.name == name:
                return branch
        return None

    @staticmethod
    def _get_pull_request_by_title(repo: github.Repository.Repository, title: str) -> github.PullRequest.PullRequest | None:
        for pull in repo.get_pulls():
            if pull.title == title:
                return pull
        return None

    @staticmethod
    def _repo_remove_invitation(repo: github.Repository.Repository, invitee: github.NamedUser.NamedUser) -> None:
        logm.debug("Removing invitations in repo '%s' for user '%s'", repo.full_name, invitee.login)

        pending_invitations = repo.get_pending_invitations()

        for invitation in pending_invitations:
            if invitation.invitee.login == invitee.login:
                logm.debug("Found invitation: '%s'", invitation.invitee.login)
                repo.remove_invitation(invitation.id)
                return
        logm.warning("Unable to find and remove invitation for '%s'", invitation.invitee.login)


    @staticmethod
    def _repo_is_invitation_for_user_pending(repo: github.Repository, user: github.NamedUser) -> bool:
        pending_invitations = repo.get_pending_invitations()
        for pending_invitation in pending_invitations:
            if pending_invitation.invitee == user:
                return True
        return False

    def _repo_create(self, org: Organization, member: Member, repo_prefix: str | None,
                     template_repo: github.Repository.Repository | None) -> None:

        repo_name = member.generate_personal_repo_name(repo_prefix)
        full_repo_name = f"{org.login}/{repo_name}"
        if self._is_repo_existing(full_repo_name):
            logm.warning("Repo already existing: '%s'. Nothing todo!", full_repo_name)
        elif template_repo:
            org.create_repo_from_template(repo_name, template_repo, private=True)
            logm.info("Created repo '%s' from template '%s'", full_repo_name, template_repo.full_name)
        else:
            org.create_repo(repo_name, private=True, auto_init=True)
            logm.info("Created repo '%s'", full_repo_name)

    def _repo_access_grant(self, repo: github.Repository.Repository, member: Member, permission: str = "pull"):
        member_named_user = self._get_named_user(member.github_username)
        if repo.has_in_collaborators(member_named_user):
            logm.warning("User already a collaborator of repo '%s' -> '%s' already pending. Nothing todo!", member, repo.full_name)
        else:
            if self._repo_is_invitation_for_user_pending(repo, member_named_user):
                logm.warning("Invitation already pending: '%s' -> '%s'. Inviting again!", member, repo.full_name)
                self._repo_remove_invitation(repo, member_named_user)
            repo.add_to_collaborators(member_named_user, permission=permission)
            logm.info("Granted access to repo '%s' -> '%s', permission: '%s'", member, repo.full_name, permission)

    def _repo_clone(self, clone_url: str, target_dir) -> None:

        logm.debug("Clone URL: '%s'", clone_url)

        os.environ["GIT_USERNAME"] = self.github_credentials.username
        os.environ["GIT_PASSWORD"] = self.github_credentials.token
        git.Repo.clone_from(clone_url, target_dir)

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
        org = self._get_org(org_name)
        repos = org.get_repos(sort="name")
        return [repo.name for repo in repos]

    def get_full_repo_names_by_org(self, org_name: str) -> List[str]:
        org = self._get_org(org_name)
        repos = org.get_repos(sort="full_name")
        return [repo.full_name for repo in repos]

    def get_user(self) -> github.NamedUser.NamedUser:
        return self.github_connection.get_user()

    def get_user_info(self, github_username: str) -> None:
        github_user = self._get_named_user(github_username)
        logm.info("Name: %s", github_user.name)
        logm.info("GitHub username: %s", github_user.login)
        logm.info("Orgs:")
        for org_name in self.get_org_names():
            logm.info("  %s", org_name)

    def class_check(self, class_name: str) -> None:
        logm.info("Validating class '%s'", class_name)

        class_to_validate = self.classes.get_class(class_name)
        logm.info("Moderators:")
        self._validate_users(class_to_validate.moderators)
        logm.info("Members:")
        self._validate_users(class_to_validate.members)

    def org_create_personal_repos(self, org_name: str, class_name: str, repo_prefix: str | None, template_repo_full_name: str | None) -> None:
        logm.info("Create class repos in org '%s' for class '%s'", org_name, class_name)

        selected_class = self.classes.get_class(class_name)
        org = self._get_org(org_name)
        template_repo = self._get_template_repo(template_repo_full_name) if template_repo_full_name else None

        with alive_bar(len(selected_class.members), title="Creating personal repo:", enrich_print=False) as bar:
            for class_member in selected_class.active_members:
                self._repo_create(org, class_member, repo_prefix, template_repo)
                bar()

            for class_member in selected_class.inactive_members:
                logm.info("Skipping repo creation of '%s' due to inactivity of class member", class_member.fullname)
                bar()

    def org_reviews_create(self, org_name: str, class_name: str, head_branch_name: str, review_branch_name: str) -> None:

        logm.info("Create reviews in '%s' for class '%s'", org_name, class_name)

        selected_class = self.classes.get_class(class_name)

        org = self._get_org(org_name)
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

                if self._get_branch_by_name(repo, review_branch_name) is None:
                    commit_history = repo.get_commits().reversed
                    first_commit = commit_history[0]

                    repo.create_git_ref(f'refs/heads/{review_branch_name}', first_commit.sha)
                    logm.info("Created '%s' branch from first commit ('%s')", review_branch_name, first_commit)
                else:
                    logm.warning("Branch '%s' already existing in repo '%s'!", review_branch_name, repo.name)

                if self._get_pull_request_by_title(repo, pr_title) is not None:
                    logm.warning("Pull-Request with '%s' already existing in repo '%s'!", review_branch_name, repo.name)
                    continue

                base_branch = self._get_branch_by_name(repo, review_branch_name)
                head_branch = self._get_branch_by_name(repo, head_branch_name)

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

    def org_access_grant_personal_repos(self, org_name: str, selected_class_members: List[Member],
                                        permission: str) -> None:
        logm.info("Grant access to personal class repos in org '%s' for the following class members:", org_name)
        org = self._get_org(org_name)

        with alive_bar(len(selected_class_members), title="Granting access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                repo_name = class_member.generate_personal_repo_name()
                repo = org.get_repo(repo_name)
                self._repo_access_grant(repo, class_member, permission)
                bar()

    def org_access_revoke_personal_repos(self, org_name: str, selected_class_members: List[Member], ) -> None:
        logm.info("Revoke access from personal class repos in org '%s' for the following class members:'", org_name)

        org = self._get_org(org_name)

        for class_member in selected_class_members:
            repo_name = class_member.generate_personal_repo_name()
            class_member_named_user = self._get_named_user(class_member.github_username)
            try:
                repo = org.get_repo(repo_name)
                repo.remove_from_collaborators(class_member_named_user)

                self._repo_remove_invitation(repo, class_member_named_user)

                logm.info("Revoked access from personal class repo '%s' for '%s'", repo.full_name, class_member)
            except github.UnknownObjectException as e:
                logm.error("%s", e)
                logm.error("Unable to revoke access for '%s'", repo_name)

    def repo_access_grant_for_class(self, full_repo_name: str, selected_class_members: List[Member], permission: str) -> None:
        logm.info("Grant class access to repo '%s' with permission '%s' for the following class members:",
                  full_repo_name, permission)

        repo = self._get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Granting access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                logm.info("Granting access for '%s' to repo '%s' with permission: '%s'", class_member, repo.full_name, permission)
                self._repo_access_grant(repo, class_member, permission)
                bar()

    def repo_access_revoke_for_class(self, full_repo_name: str, selected_class_members: List[Member], ) -> None:
        logm.info("Revoke class access from repo '%s' for the following class members.", full_repo_name)

        repo = self._get_repo(full_repo_name)

        with alive_bar(len(selected_class_members), title="Revoke access:", enrich_print=False) as bar:
            for class_member in selected_class_members:
                class_member_named_user = self._get_named_user(class_member.github_username)
                try:
                    repo.remove_from_collaborators(class_member_named_user)
                    self._repo_remove_invitation(repo, class_member_named_user)

                    logm.info("Revoked access from repo '%s' for user '%s'", repo.full_name, class_member)
                except github.UnknownObjectException as e:
                    logm.error("%s", e)
                    logm.error("Unable to revoke access from repo '%s' for user '%s'", repo.full_name, class_member)
                bar()

    def repo_print_details(self, full_repo_name: str) -> None:
        repo = self._get_repo(full_repo_name)

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

    def clone_org(self, org_name: str, working_dir: Path) -> None:
        logm.info("Cloning all repos of org '%s'", org_name)

        backup_dir = working_dir / org_name
        backup_dir.mkdir(exist_ok=False)

        org = self._get_org(org_name)
        repos = org.get_repos()

        with alive_bar(repos.totalCount, title="Cloning repos:", enrich_print=False) as bar:
            for repo in repos:
                backup_repo_dir = backup_dir / repo.name
                logm.info("Cloning repo '%s' -> '%s'", repo.clone_url, backup_repo_dir)
                backup_repo_dir.mkdir()
                self._repo_clone(repo.clone_url, backup_repo_dir)
                bar()
