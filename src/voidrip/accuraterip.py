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
# from os import PathLike
from dataclasses import dataclass
from os import PathLike
from typing import Tuple, Optional, List

from . import tools
from . import cd
from pathlib import Path, PosixPath


# notes:
# see https://github.com/tuffy/python-audio-tools/blob/master/audiotools/accuraterip.py#L286
# on how to query accuraterip


class AccurateRipException(Exception):
    pass


@dataclass
class ARChecksum:
    crc1: int
    crc2: int

    def __repr__(self) -> str:
        return f"({self.crc1:08x},{self.crc2:08x})"


class AccurateRip:
    #BINARY = PosixPath("/home/bas/NerdProjecten/cdrip/accuraterip/accuraterip")
    BINARY = PosixPath("/home/bas/pycharm/cdrip/accuraterip/accuraterip")

    def __init__(self, disc: cd.Disc, wav_file: Path):
        if not self.BINARY.exists():
            raise FileNotFoundError(f"Cannot find accuraterip binary at f{self.BINARY}")
        self._disc = disc
        self._wav = wav_file

    @property
    def offset(self) -> int:
        return self._disc.cdplayer.offset

    @classmethod
    def _run_binary(cls, args: List[str]) -> List[ARChecksum]:
        result = tools.execcmd(cls.BINARY, args)
        if result.returncode != 0:
            raise AccurateRipException(f"Accuraterip run failed with code {result.returncode}: {result.stderr}")

        # now parse the stdout, expecting output like:
        # track01 03:00:00.000   7938000 435cff30 140a7894
        chksums: List[ARChecksum] = []
        for line in result.stdout.splitlines():
            (track, _, _, crc1_s, crc2_s) = line.split()
            if not track.startswith("track"):
                raise AccurateRipException(f"Could not parse accuraterip output: \n{result.stdout}")
            crc1 = int(crc1_s, 16)
            crc2 = int(crc2_s, 16)
            chksums.append(ARChecksum(crc1, crc2))

        return chksums

    def checksum(self, filename: PathLike,
                 sample_start: Optional[int] = None,
                 sample_num: Optional[int] = None) -> ARChecksum:
        args = [str(filename)]
        if sample_start is not None:
            args += [f'{sample_start:d}s']
        if sample_num is not None:
            args += [f'{sample_num:d}s']

        chksums = self._run_binary(args)
        if len(chksums) > 1:
            raise AccurateRipException(f"Found {len(chksums)} while expecting only 1")

        return chksums[0]

    # get checksums for multiple tracks in a single file
    # todo: make a proper object to describe the tracks
    def checksum_multi(self, filename: Path, tracks: List[Tuple[int, int]], offset: int = 0) -> List[ARChecksum]:
        if not filename.exists():
            raise FileNotFoundError(f"Audio file '{filename}' not found")

        args = [str(filename)]
        args += ["-o", offset]
        args += ["{}s,{}s".format(*t) for t in tracks]

        chksums = self._run_binary(args)
        return chksums

    def checksum_disc(self) -> List[ARChecksum]:
        track_spec = [(t.first_sample, t.length_samples) for t in self._disc.tracks]
        chksums = self.checksum_multi(self._wav, track_spec, self.offset)
        print(chksums)
        return [ARChecksum(0, 0)]
