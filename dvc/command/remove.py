import argparse
import logging

import dvc.prompt as prompt
from dvc.command.base import CmdBase, append_doc_link
from dvc.exceptions import DvcException

logger = logging.getLogger(__name__)


class CmdRemove(CmdBase):
    def _is_outs_only(self, target):
        if not self.args.purge:
            return True

        if self.args.force:
            return False

        msg = "Are you sure you want to remove '{}' with its outputs?".format(
            target
        )

        if prompt.confirm(msg):
            return False

        raise DvcException(
            "Cannot purge without a confirmation from the user."
            " Use `-f` to force."
        )

    def run(self):
        for target in self.args.targets:
            try:
                outs_only = self._is_outs_only(target)
                self.repo.remove(target, outs_only=outs_only)
            except DvcException:
                logger.exception(f"failed to remove '{target}'")
                return 1
        return 0


def add_parser(subparsers, parent_parser):
    REMOVE_HELP = "Remove DVC-tracked files or directories."
    remove_parser = subparsers.add_parser(
        "remove",
        parents=[parent_parser],
        description=append_doc_link(REMOVE_HELP, "remove"),
        help=REMOVE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    remove_parser_group = remove_parser.add_mutually_exclusive_group()
    remove_parser_group.add_argument(
        "-o",
        "--outs",
        action="store_true",
        default=True,
        help="Only remove DVC-file outputs. (Default)",
    )
    remove_parser_group.add_argument(
        "-p",
        "--purge",
        action="store_true",
        default=False,
        help="Remove DVC-file and all its outputs.",
    )
    remove_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Force purge.",
    )
    remove_parser.add_argument(
        "targets", nargs="+", help="DVC-files to remove."
    )
    remove_parser.set_defaults(func=CmdRemove)
