import argparse
import logging
import sys

from dvc.command.base import CmdBaseNoRepo, append_doc_link
from dvc.command.ls.ls_colors import LsColors
from dvc.exceptions import DvcException

logger = logging.getLogger(__name__)


def _prettify(entries, with_color=False):
    if with_color:
        ls_colors = LsColors()
        fmt = ls_colors.format
    else:

        def fmt(entry):
            return entry["path"]

    return [fmt(entry) for entry in entries]


class CmdList(CmdBaseNoRepo):
    def run(self):
        from dvc.repo import Repo

        try:
            entries = Repo.ls(
                self.args.url,
                self.args.path,
                rev=self.args.rev,
                recursive=self.args.recursive,
                outs_only=self.args.outs_only,
            )
            if entries:
                entries = _prettify(entries, sys.stdout.isatty())
                logger.info("\n".join(entries))
            return 0
        except DvcException:
            logger.exception(f"failed to list '{self.args.url}'")
            return 1


def add_parser(subparsers, parent_parser):
    LIST_HELP = (
        "List repository contents, including files"
        " and directories tracked by DVC and by Git."
    )
    list_parser = subparsers.add_parser(
        "list",
        parents=[parent_parser],
        description=append_doc_link(LIST_HELP, "list"),
        help=LIST_HELP,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    list_parser.add_argument("url", help="Location of DVC repository to list")
    list_parser.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="Recursively list files.",
    )
    list_parser.add_argument(
        "--outs-only", action="store_true", help="Show only DVC outputs."
    )
    list_parser.add_argument(
        "--rev",
        nargs="?",
        help="Git revision (e.g. SHA, branch, tag)",
        metavar="<commit>",
    )
    list_parser.add_argument(
        "path",
        nargs="?",
        help="Path to directory within the repository to list outputs for",
    )
    list_parser.set_defaults(func=CmdList)
