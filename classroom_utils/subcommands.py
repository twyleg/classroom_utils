# Copyright (C) 2024 twyleg
import argparse
import sys
from typing import Dict

from classroom_utils import __version__


class Command:
    def __init__(self, parser):
        self.parser = parser
        self.subparser = None
        self.subcommands: Dict[str, Command] = {}
        if hasattr(self, 'handle'):
            self.parser.set_defaults(func=self.handle)
        else:
            self.parser.set_defaults(func=self.default_handle)

        self.parser.add_argument(
            "-vv",
            "--verbose",
            help="Run with verbose output.",
            action='store_true',
        )

    def default_handle(self, args: argparse.Namespace):
        print("Error: Function not yet implemented!")

    def add_subcommand(self, command: str, command_type=None) -> "Command":

        command_chain = command.split(" ")

        if len(command_chain) == 1:

            if self.subparser is None:
                self.subparser = self.parser.add_subparsers(required=not hasattr(self, 'handle'), title="subcommands")

            parser = self.subparser.add_parser(command)
            subcommand = Command(parser) if command_type is None else command_type(parser)
            self.subcommands[command] = subcommand
            return subcommand

        else:
            next_command = command_chain[0]
            remaining_commands = " ".join(command_chain[1:])
            return self.subcommands[next_command].add_subcommand(remaining_commands, command_type)


class RootCommand(Command):
    def __init__(self):
        super().__init__(argparse.ArgumentParser(usage="classroom_utils"))

        self.parser.add_argument(
            "-v",
            "--version",
            help="Show version and exit",
            action="version",
            version=__version__,
        )

    def handle(self, args: argparse.Namespace):
        pass

    def parse(self, args=None) -> argparse.Namespace:
        if args is None:
            args = sys.argv[1:]
        return self.parser.parse_args(args)