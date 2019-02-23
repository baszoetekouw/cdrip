import subprocess
import tempfile
from typing import List
from os import PathLike


def execcmd(cmd: str, args: List[str] = (), cwd: PathLike=None) -> None:
	tmp = cwd or tempfile.TemporaryDirectory()

	#TODO: check if cmd is executable
	cmdline = [cmd] + list(args)
	print(f'Running: "{cmdline}"')
	subprocess.run(cmdline, cwd=str(tmp))

