import subprocess
import tempfile
from typing import List, Union
from os import PathLike
from pathlib import Path


def execcmd(cmd: Union[Path, PathLike],
            args: List[str] = (),
            cwd: Union[Path, PathLike] = None,
            show_output: bool = False
            ) -> subprocess.CompletedProcess:
    if cwd is not None:
        tmp = cwd
    else:
        thedir = tempfile.TemporaryDirectory()
        tmp = thedir.name

    # TODO: check if cmd is executable1
    cmdline = [str(cmd)] + [str(a) for a in args]
    print(f'Running: "{" ".join(cmdline)}"')

    if show_output:
        result = subprocess.check_call(cmdline, cwd=tmp, stdout=subprocess.STDOUT)
    else:
        result = subprocess.run(cmdline, cwd=tmp, capture_output=True, encoding='utf-8')

    return result


def script_dir() -> Path:
    return Path(__file__).parent.parent.absolute()
