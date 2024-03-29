# Copyright (C) 2024 twyleg
from classroom_utils import __version__
from classroom_utils.cli import *


logm = logging.getLogger("main")
FORMAT = "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s"


def main() -> None:
    root_command = PromptRootCommand()
    root_command.add_subcommand(command="local")
    root_command.add_subcommand(command="local mkdir", command_type=LocalClassMkdirSubCommand)
    root_command.add_subcommand(command="github", command_type=GithubSubCommand)
    root_command.add_subcommand(command="github class")
    root_command.add_subcommand(command="github class check", command_type=GithubClassCheckSubCommand)
    root_command.add_subcommand(command="github org", command_type=GithubOrgSubCommand)
    root_command.add_subcommand(command="github org init", command_type=GithubOrgInitSubCommand)
    root_command.add_subcommand(command="github org clone", command_type=GithubOrgCloneSubCommand)
    root_command.add_subcommand(command="github org access", command_type=GithubOrgAccessSubCommand)
    root_command.add_subcommand(command="github org access grant", command_type=GithubOrgAccessGrantSubCommand)
    root_command.add_subcommand(command="github org access revoke", command_type=GithubOrgAccessRevokeSubCommand)
    root_command.add_subcommand(command="github org review")
    root_command.add_subcommand(command="github org review create", command_type=GithubOrgReviewCreateSubCommand)
    root_command.add_subcommand(command="github org review status", command_type=GithubOrgReviewStatusSubCommand)
    root_command.add_subcommand(command="github repo", command_type=GithubRepoSubCommand)
    root_command.add_subcommand(command="github repo create")
    root_command.add_subcommand(command="github repo access")
    root_command.add_subcommand(command="github repo access grant", command_type=GithubRepoAccessGrantSubCommand)
    root_command.add_subcommand(command="github repo access revoke", command_type=GithubRepoAccessRevokeSubCommand)

    args = root_command.parse()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=log_level, force=True)

    logm.info("classroom_utils started!")
    logm.info(__version__)
    logm.debug("Log level: %s", logging.getLevelName(log_level))
    logm.debug("Arguments: %s", args)
    logm.debug("Command: %s", args.func.__name__)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        logging.info("Process aborted by user! Exiting...")


if __name__ == "__main__":
    main()
