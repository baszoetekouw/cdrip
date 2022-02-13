#
# <one line to give the program's name and a brief idea of what it does.>
# Copyright (C) 2018  Bas Zoetekouw <bas.zoetekouw@surfnet.nl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
from os import PathLike
from typing import Tuple, Optional, List

from . import tools
from pathlib import Path, PosixPath


class AccurateRipException(Exception):
	pass


class AccurateRip:
	BINARY = PosixPath("/home/bas/NerdProjecten/cdrip/accuraterip/accuraterip")

	def __init__(self):
		if not self.BINARY.exists():
			raise FileNotFoundError(f"Cannot file accuraterip binary at f{self.BINARY}")

	def _run_binary(self, filename: Path, sample_start: int = None, sample_num: int = None) -> Tuple[int, int]:
		if not filename.exists():
			raise FileNotFoundError(f"Audio file '{filename}' not found")

		args = [str(filename)]
		if sample_start is not None:
			args += [f'{sample_start:d}']
		if sample_num is not None:
			args += [f'{sample_num:d}']

		result = tools.execcmd(self.BINARY, args)
		if result.returncode != 0:
			raise AccurateRipException(f"Accuraterip run failed with code {result.returncode}: {result.stderr}")

		# now parse the stdout, expecting two lines each containing a 32 bit hex number
		lines = result.stdout.splitlines()
		if len(lines) != 2:
			raise AccurateRipException(f"Could not parse accuraterip output: \n{result.stdout}")
		crc1 = int(lines[0], 16)
		crc2 = int(lines[1], 16)

		return crc1, crc2

	def checksum(self, filename: Path,
				sample_start: Optional[int] = None,
				sample_num: Optional[int] = None) -> Tuple[int, int]:
		return self._run_binary(filename, sample_start, sample_num)

	# get checksums for multiple tracks in a single file
	# todo: make a proper object to describe the tracks
	def checksum_multi(self, filename: Path, tracks: List[Tuple[int, int]]):
		checksums: List[Tuple[int, int]] = []
		for track in tracks:
			sample_start = track[0]
			sample_num = track[1]
			crc1, crc2 = self.checksum(filename, sample_start, sample_num)
			checksums.append((crc1, crc2))
		return checksums
