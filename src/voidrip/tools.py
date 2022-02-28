from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from enum import Enum
from inspect import ismethod
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


class AudioRipperJSONEncoder(json.JSONEncoder):
    @staticmethod
    def has_method(instance, method):
        return hasattr(instance, method) and ismethod(getattr(instance, method))

    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf_8')
            except SyntaxError:
                try:
                    return obj.decode('iso8859_15')
                except SyntaxError:
                    try:
                        return obj.decode('utf_16')
                    except SyntaxError:
                        return ''.join(
                            [bytes(b).decode('ASCII') if 32 <= b <= 126 else "?" for b in obj]
                        )
        elif isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, PathLike):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif self.has_method(obj, "as_dict"):
            return obj.as_dict()

        return super(AudioRipperJSONEncoder, self).default(obj)
