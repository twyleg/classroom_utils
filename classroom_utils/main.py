# Copyright (C) 2024 twyleg
from subcommands import RootCommand
from classroom_utils.cli import *

FORMAT = "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s"


def main() -> None:

    root_command = RootCommand()
    root_command.add_subcommand(command="local")
    root_command.add_subcommand(command="local mkdir", command_type=LocalClassMkdirSubCommand)
    root_command.add_subcommand(command="github", command_type=GithubSubCommand)
    root_command.add_subcommand(command="github check")
    root_command.add_subcommand(command="github check class", command_type=GithubCheckClassSubCommand)
    root_command.add_subcommand(command="github org", command_type=GithubOrgSubCommand)
    root_command.add_subcommand(command="github org init", command_type=GithubOrgInitSubCommand)
    root_command.add_subcommand(command="github org access", command_type=GithubOrgAccessSubCommand)
    root_command.add_subcommand(command="github org access grant", command_type=GithubOrgAccessGrantSubCommand)
    root_command.add_subcommand(command="github org access revoke", command_type=GithubOrgAccessRevokeSubCommand)
    root_command.add_subcommand(command="github org review")
    root_command.add_subcommand(command="github org review create", command_type=GithubOrgReviewCreateSubCommand)
    root_command.add_subcommand(command="github org review status", command_type=GithubOrgReviewStatusSubCommand)

    args = root_command.parse()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=log_level, force=True)

    logging.info("classroom_utils started!")
    logging.debug("Log level: %s", logging.getLevelName(log_level))
    logging.debug("Arguments: %s", args)
    logging.debug("Command: %s", args.func.__name__)

    args.func(args)


if __name__ == "__main__":
    main()