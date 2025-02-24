from funcy import group_by

from dvc.scm.tree import WorkingTree


def brancher(  # noqa: E302
    self, revs=None, all_branches=False, all_tags=False, all_commits=False
):
    """Generator that iterates over specified revisions.

    Args:
        revs (list): a list of revisions to iterate over.
        all_branches (bool): iterate over all available branches.
        all_commits (bool): iterate over all commits.
        all_tags (bool): iterate over all available tags.

    Yields:
        str: the display name for the currently selected tree, it could be:
            - a git revision identifier
            - empty string it there is no branches to iterate over
            - "Working Tree" if there are uncommitted changes in the SCM repo
    """
    if not any([revs, all_branches, all_tags, all_commits]):
        yield ""
        return

    saved_tree = self.tree
    revs = revs.copy() if revs else []

    scm = self.scm

    self.tree = WorkingTree(self.root_dir)
    yield "working tree"

    if revs and "working tree" in revs:
        revs.remove("working tree")

    if all_commits:
        revs = scm.list_all_commits()
    else:
        if all_branches:
            revs.extend(scm.list_branches())

        if all_tags:
            revs.extend(scm.list_tags())

    try:
        if revs:
            for sha, names in group_by(scm.resolve_rev, revs).items():
                self.tree = scm.get_tree(sha)
                yield ", ".join(names)
    finally:
        self.tree = saved_tree
