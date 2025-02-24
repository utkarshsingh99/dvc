import os
import shutil

import pytest

from dvc.exceptions import PathMissingError
from dvc.repo import Repo
from dvc.scm.base import CloneError

FS_STRUCTURE = {
    "README.md": "content",
    "model/script.py": "content",
    "model/train.py": "content",
    ".gitignore": "content",
}

DVC_STRUCTURE = {
    "structure.xml": "content",
    "data/subcontent/data.xml": "content",
    "data/subcontent/statistics/data.csv": "content",
    "model/people.csv": "content",
}


def match_files(files, expected_files):
    left = {(f["path"], f["isout"]) for f in files}
    right = {(os.path.join(*args), isout) for (args, isout) in expected_files}
    assert left == right


def create_dvc_pipeline(tmp_dir, dvc):
    script = os.linesep.join(
        [
            "from pathlib import Path",
            "Path({}).touch()".format(os.path.join("out", "file")),
        ]
    )
    tmp_dir.scm_gen({"script.py": script}, commit="init")
    tmp_dir.dvc_gen({"dep": "content"}, commit="init dvc")
    dvc.run(
        **{
            "command": "python script.py",
            "outs": [os.path.join("out", "file")],
            "deps": ["dep"],
            "fname": "out.dvc",
            "single_stage": True,
        }
    )
    tmp_dir.scm_add(["out.dvc"], commit="run")
    shutil.rmtree("out")


def test_ls_repo(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    files = Repo.ls(os.fspath(tmp_dir))
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("structure.xml.dvc",), False),
            (("model",), False),
            (("data",), False),
            (("structure.xml",), True),
        ),
    )


def test_ls_repo_with_color(tmp_dir, dvc, scm, mocker, monkeypatch, caplog):
    import logging
    from dvc.cli import parse_args

    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    monkeypatch.setenv("LS_COLORS", "rs=0:di=01;34:*.xml=01;31:*.dvc=01;33:")
    cli_args = parse_args(["list", os.fspath(tmp_dir)])
    cmd = cli_args.func(cli_args)

    caplog.clear()
    mocker.patch("sys.stdout.isatty", return_value=True)
    with caplog.at_level(logging.INFO, logger="dvc.command.ls"):
        assert cmd.run() == 0

    assert caplog.records[-1].msg == "\n".join(
        [
            ".gitignore",
            "README.md",
            "\x1b[01;34mdata\x1b[0m",
            "\x1b[01;34mmodel\x1b[0m",
            "\x1b[01;31mstructure.xml\x1b[0m",
            "\x1b[01;33mstructure.xml.dvc\x1b[0m",
        ]
    )


def test_ls_repo_recursive(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    files = Repo.ls(os.fspath(tmp_dir), recursive=True)
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("structure.xml.dvc",), False),
            (("model", "script.py"), False),
            (("model", "train.py"), False),
            (("model", "people.csv.dvc"), False),
            (("data", "subcontent", "data.xml.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv"), True),
            (("data", "subcontent", "statistics", ".gitignore"), False),
            (("data", "subcontent", "data.xml"), True),
            (("data", "subcontent", ".gitignore"), False),
            (("model", "people.csv"), True),
            (("model", ".gitignore"), False),
            (("structure.xml",), True),
        ),
    )


def test_ls_repo_outs_only_recursive(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    files = Repo.ls(os.fspath(tmp_dir), recursive=True, outs_only=True)
    match_files(
        files,
        (
            (("data", "subcontent", "statistics", "data.csv"), True),
            (("data", "subcontent", "data.xml"), True),
            (("model", "people.csv"), True),
            (("structure.xml",), True),
        ),
    )


def test_ls_repo_with_path_dir(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    files = Repo.ls(os.fspath(tmp_dir), path="model")
    match_files(
        files,
        (
            (("script.py",), False),
            (("train.py",), False),
            (("people.csv",), True),
            (("people.csv.dvc",), False),
            ((".gitignore",), False),
        ),
    )


def test_ls_repo_with_path_dir_outs_only_empty(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")
    tmp_dir.scm_gen({"folder/.keep": "content"}, commit="add .keep")

    with pytest.raises(PathMissingError):
        Repo.ls(os.fspath(tmp_dir), path="folder", outs_only=True)


def test_ls_repo_with_path_subdir(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    path = os.path.join("data", "subcontent")
    files = Repo.ls(os.fspath(tmp_dir), path)
    match_files(
        files,
        (
            (("data.xml",), True),
            (("data.xml.dvc",), False),
            (("statistics",), False),
            ((".gitignore",), False),
        ),
    )


def test_ls_repo_with_path_subdir_outs_only(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    path = os.path.join("data", "subcontent")
    files = Repo.ls(os.fspath(tmp_dir), path, outs_only=True)
    match_files(files, ((("data.xml",), True), (("statistics",), False),))


def test_ls_repo_with_path_subdir_outs_only_recursive(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    path = os.path.join("data", "subcontent")
    files = Repo.ls(os.fspath(tmp_dir), path, outs_only=True, recursive=True)
    match_files(
        files, ((("data.xml",), True), (("statistics", "data.csv"), True),)
    )


def test_ls_repo_with_path_file_out(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    path = os.path.join("data", "subcontent", "data.xml")
    files = Repo.ls(os.fspath(tmp_dir), path)
    match_files(files, ((("data.xml",), True),))


def test_ls_repo_with_file_path_fs(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    path = "README.md"
    files = Repo.ls(os.fspath(tmp_dir), path, recursive=True)
    match_files(files, ((("README.md",), False),))


def test_ls_repo_with_missed_path(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    with pytest.raises(PathMissingError) as exc_info:
        Repo.ls(os.fspath(tmp_dir), path="missed_path")
    assert not exc_info.value.output_only


def test_ls_repo_with_missed_path_outs_only(tmp_dir, dvc, scm):
    tmp_dir.scm_gen(FS_STRUCTURE, commit="init")
    tmp_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    with pytest.raises(PathMissingError) as exc_info:
        Repo.ls(
            os.fspath(tmp_dir),
            path="missed_path",
            recursive=True,
            outs_only=True,
        )
    assert exc_info.value.output_only


def test_ls_repo_with_removed_dvc_dir(tmp_dir, dvc, scm):
    create_dvc_pipeline(tmp_dir, dvc)

    files = Repo.ls(os.fspath(tmp_dir))
    match_files(
        files,
        (
            (("script.py",), False),
            (("dep.dvc",), False),
            (("out.dvc",), False),
            (("dep",), True),
            (("out",), False),
            ((".gitignore",), False),
        ),
    )


def test_ls_repo_with_removed_dvc_dir_recursive(tmp_dir, dvc, scm):
    create_dvc_pipeline(tmp_dir, dvc)

    files = Repo.ls(os.fspath(tmp_dir), recursive=True)
    match_files(
        files,
        (
            (("script.py",), False),
            (("dep.dvc",), False),
            (("out.dvc",), False),
            (("dep",), True),
            (("out", "file"), True),
            ((".gitignore",), False),
        ),
    )


def test_ls_repo_with_removed_dvc_dir_with_path_dir(tmp_dir, dvc, scm):
    create_dvc_pipeline(tmp_dir, dvc)

    path = "out"
    files = Repo.ls(os.fspath(tmp_dir), path)
    match_files(files, ((("file",), True),))


def test_ls_repo_with_removed_dvc_dir_with_path_file(tmp_dir, dvc, scm):
    create_dvc_pipeline(tmp_dir, dvc)

    path = os.path.join("out", "file")
    files = Repo.ls(os.fspath(tmp_dir), path)
    match_files(files, ((("file",), True),))


def test_ls_remote_repo(erepo_dir):
    with erepo_dir.chdir():
        erepo_dir.scm_gen(FS_STRUCTURE, commit="init")
        erepo_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    url = f"file://{erepo_dir}"
    files = Repo.ls(url)
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("structure.xml.dvc",), False),
            (("model",), False),
            (("data",), False),
            (("structure.xml",), True),
        ),
    )


def test_ls_remote_repo_recursive(erepo_dir):
    with erepo_dir.chdir():
        erepo_dir.scm_gen(FS_STRUCTURE, commit="init")
        erepo_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    url = f"file://{erepo_dir}"
    files = Repo.ls(url, recursive=True)
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("structure.xml.dvc",), False),
            (("model", "script.py"), False),
            (("model", "train.py"), False),
            (("model", "people.csv.dvc"), False),
            (("data", "subcontent", "data.xml.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv"), True),
            (("data", "subcontent", "statistics", ".gitignore"), False),
            (("data", "subcontent", "data.xml"), True),
            (("data", "subcontent", ".gitignore"), False),
            (("model", "people.csv"), True),
            (("model", ".gitignore"), False),
            (("structure.xml",), True),
        ),
    )


def test_ls_remote_git_only_repo_recursive(git_dir):
    with git_dir.chdir():
        git_dir.scm_gen(FS_STRUCTURE, commit="init")

    url = f"file://{git_dir}"
    files = Repo.ls(url, recursive=True)
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("model", "script.py"), False),
            (("model", "train.py"), False),
        ),
    )


def test_ls_remote_repo_with_path_dir(erepo_dir):
    with erepo_dir.chdir():
        erepo_dir.scm_gen(FS_STRUCTURE, commit="init")
        erepo_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    url = f"file://{erepo_dir}"
    path = "model"
    files = Repo.ls(url, path)
    match_files(
        files,
        (
            (("script.py",), False),
            (("train.py",), False),
            (("people.csv",), True),
            (("people.csv.dvc",), False),
            ((".gitignore",), False),
        ),
    )


def test_ls_remote_repo_with_rev(erepo_dir):
    with erepo_dir.chdir():
        erepo_dir.scm_gen(FS_STRUCTURE, commit="init")
        erepo_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")

    rev = erepo_dir.scm.list_all_commits()[1]
    url = f"file://{erepo_dir}"
    files = Repo.ls(url, rev=rev)
    match_files(
        files,
        (
            ((".gitignore",), False),
            (("README.md",), False),
            (("model",), False),
        ),
    )


def test_ls_remote_repo_with_rev_recursive(erepo_dir):
    with erepo_dir.chdir():
        erepo_dir.dvc_gen(DVC_STRUCTURE, commit="dvc")
        erepo_dir.scm_gen(FS_STRUCTURE, commit="init")

    rev = erepo_dir.scm.list_all_commits()[1]
    url = f"file://{erepo_dir}"
    files = Repo.ls(url, rev=rev, recursive=True)
    match_files(
        files,
        (
            (("structure.xml.dvc",), False),
            (("model", "people.csv.dvc"), False),
            (("data", "subcontent", "data.xml.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv.dvc"), False),
            (("data", "subcontent", "statistics", "data.csv"), True),
            (("data", "subcontent", "statistics", ".gitignore"), False),
            (("data", "subcontent", "data.xml"), True),
            (("data", "subcontent", ".gitignore"), False),
            (("model", "people.csv"), True),
            (("model", ".gitignore"), False),
            (("structure.xml",), True),
            ((".gitignore",), False),
        ),
    )


def test_ls_not_existed_url():
    from time import time

    dirname = "__{}_{}".format("not_existed", time())
    with pytest.raises(CloneError):
        Repo.ls(dirname, recursive=True)


def test_ls_shows_pipeline_tracked_outs(tmp_dir, dvc, scm, run_copy):
    from dvc.dvcfile import PIPELINE_FILE, PIPELINE_LOCK

    tmp_dir.gen("foo", "foo")
    run_copy("foo", "bar", name="copy-foo-bar")
    dvc.scm.add([PIPELINE_FILE, PIPELINE_LOCK])
    dvc.scm.commit("add pipeline stage")

    files = Repo.ls(os.curdir, outs_only=True)
    match_files(files, ((("bar",), True),))
