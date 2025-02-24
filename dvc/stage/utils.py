import os
import pathlib
from itertools import product

from dvc import dependency, output
from dvc.utils.fs import path_isin

from ..remote import LocalRemote, S3Remote
from ..utils import dict_md5, relpath
from .exceptions import (
    MissingDataSource,
    StagePathNotDirectoryError,
    StagePathNotFoundError,
    StagePathOutsideError,
)


def check_stage_path(repo, path, is_wdir=False):
    assert repo is not None

    error_msg = "{wdir_or_path} '{path}' {{}}".format(
        wdir_or_path="stage working dir" if is_wdir else "file path",
        path=path,
    )

    real_path = os.path.realpath(path)
    if not os.path.exists(real_path):
        raise StagePathNotFoundError(error_msg.format("does not exist"))

    if not os.path.isdir(real_path):
        raise StagePathNotDirectoryError(error_msg.format("is not directory"))

    proj_dir = os.path.realpath(repo.root_dir)
    if real_path != proj_dir and not path_isin(real_path, proj_dir):
        raise StagePathOutsideError(error_msg.format("is outside of DVC repo"))


def fill_stage_outputs(stage, **kwargs):
    assert not stage.outs

    keys = [
        "outs_persist",
        "outs_persist_no_cache",
        "metrics_no_cache",
        "metrics",
        "plots_no_cache",
        "plots",
        "outs_no_cache",
        "outs",
    ]

    stage.outs = []
    for key in keys:
        stage.outs += output.loads_from(
            stage,
            kwargs.get(key, []),
            use_cache="no_cache" not in key,
            persist="persist" in key,
            metric="metrics" in key,
            plot="plots" in key,
        )


def fill_stage_dependencies(stage, deps=None, erepo=None, params=None):
    assert not stage.deps
    stage.deps = []
    stage.deps += dependency.loads_from(stage, deps or [], erepo=erepo)
    stage.deps += dependency.loads_params(stage, params or [])


def check_circular_dependency(stage):
    from dvc.exceptions import CircularDependencyError

    circular_dependencies = {d.path_info for d in stage.deps} & {
        o.path_info for o in stage.outs
    }

    if circular_dependencies:
        raise CircularDependencyError(str(circular_dependencies.pop()))


def check_duplicated_arguments(stage):
    from dvc.exceptions import ArgumentDuplicationError
    from collections import Counter

    path_counts = Counter(edge.path_info for edge in stage.deps + stage.outs)

    for path, occurrence in path_counts.items():
        if occurrence > 1:
            raise ArgumentDuplicationError(str(path))


def check_missing_outputs(stage):
    paths = [str(out) for out in stage.outs if not out.exists]
    if paths:
        raise MissingDataSource(paths)


def stage_dump_eq(stage_cls, old_d, new_d):
    # NOTE: need to remove checksums from old dict in order to compare
    # it to the new one, since the new one doesn't have checksums yet.
    old_d.pop(stage_cls.PARAM_MD5, None)
    new_d.pop(stage_cls.PARAM_MD5, None)
    outs = old_d.get(stage_cls.PARAM_OUTS, [])
    for out in outs:
        out.pop(LocalRemote.PARAM_CHECKSUM, None)
        out.pop(S3Remote.PARAM_CHECKSUM, None)

    # outs and deps are lists of dicts. To check equality, we need to make
    # them independent of the order, so, we convert them to dicts.
    combination = product(
        [old_d, new_d], [stage_cls.PARAM_DEPS, stage_cls.PARAM_OUTS]
    )
    for coll, key in combination:
        if coll.get(key):
            coll[key] = {item["path"]: item for item in coll[key]}
    return old_d == new_d


def compute_md5(stage):
    from dvc.output.base import BaseOutput

    d = stage.dumpd()

    # Remove md5 and meta, these should not affect stage md5
    d.pop(stage.PARAM_MD5, None)
    d.pop(stage.PARAM_META, None)

    # Ignore the wdir default value. In this case DVC-file w/o
    # wdir has the same md5 as a file with the default value specified.
    # It's important for backward compatibility with pipelines that
    # didn't have WDIR in their DVC-files.
    if d.get(stage.PARAM_WDIR) == ".":
        del d[stage.PARAM_WDIR]

    return dict_md5(
        d,
        exclude=[
            stage.PARAM_LOCKED,
            BaseOutput.PARAM_METRIC,
            BaseOutput.PARAM_PERSIST,
        ],
    )


def resolve_wdir(wdir, path):
    rel_wdir = relpath(wdir, os.path.dirname(path))
    return pathlib.PurePath(rel_wdir).as_posix() if rel_wdir != "." else None


def get_dump(stage):
    return {
        key: value
        for key, value in {
            stage.PARAM_MD5: stage.md5,
            stage.PARAM_CMD: stage.cmd,
            stage.PARAM_WDIR: resolve_wdir(stage.wdir, stage.path),
            stage.PARAM_LOCKED: stage.locked,
            stage.PARAM_DEPS: [d.dumpd() for d in stage.deps],
            stage.PARAM_OUTS: [o.dumpd() for o in stage.outs],
            stage.PARAM_ALWAYS_CHANGED: stage.always_changed,
        }.items()
        if value
    }
