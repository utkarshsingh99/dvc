import argparse
import logging

from dvc.command.base import CmdBase, append_doc_link
from dvc.exceptions import DvcException

logger = logging.getLogger(__name__)


class CmdCommit(CmdBase):
    def run(self):
        if not self.args.targets:
            self.args.targets = [None]

        for target in self.args.targets:
            try:
                self.repo.commit(
                    target,
                    with_deps=self.args.with_deps,
                    recursive=self.args.recursive,
                    force=self.args.force,
                )
            except DvcException:
                logger.exception(
                    "failed to commit{}".format(
                        (" " + target) if target else ""
                    )
                )
                return 1
        return 0


def add_parser(subparsers, parent_parser):
    COMMIT_HELP = "Save changed data to cache and update DVC-files."

    commit_parser = subparsers.add_parser(
        "commit",
        parents=[parent_parser],
        description=append_doc_link(COMMIT_HELP, "commit"),
        help=COMMIT_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commit_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Commit even if hash value for dependencies/outputs changed.",
    )
    commit_parser.add_argument(
        "-d",
        "--with-deps",
        action="store_true",
        default=False,
        help="Commit all dependencies of the specified target.",
    )
    commit_parser.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        default=False,
        help="Commit cache for subdirectories of the specified directory.",
    )
    commit_parser.add_argument(
        "targets",
        nargs="*",
        help="DVC-files to commit. Optional. "
        "(Finds all DVC-files in the workspace by default.)",
    )
    commit_parser.set_defaults(func=CmdCommit)
