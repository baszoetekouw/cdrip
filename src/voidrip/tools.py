import subprocess
import tempfile
from typing import List

def execcmd(cmd: str, args: List[str] = (), cwd: tempfile.TemporaryDirectory=None) -> None:
	tmp = cwd or tempfile.TemporaryDirectory()

	#TODO: check if cmd is executable
	cmdline = [cmd] + list(args)
	print(f'Running: "{cmdline}"')
	subprocess.run(cmdline, cwd=tmp.name)

