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
from __future__ import annotations

import urllib.request
import struct
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path, PosixPath
from typing import Dict, Tuple, Optional, List

from . import tools
from . import cd

# notes:
# see https://github.com/tuffy/python-audio-tools/blob/master/audiotools/accuraterip.py#L286
# on how to query accuraterip


class AccurateRipException(Exception):
    pass


@dataclass
class AccurateRipID:
    BASEURL = "http://www.accuraterip.com/accuraterip"

    num_tracks: int
    id1: int
    id2: int
    id3: int

    @property
    def id(self) -> str:
        return f"dBAR-{self.num_tracks:03d}-{self.id1:08x}-{self.id2:08x}-{self.id3:08x}"

    def __repr__(self) -> str:
        return self.id

    def as_dict(self) -> Dict[str, str]:
        return self.__dict__

    @property
    def url(self):
        i1 = f"{self.id1:08x}"
        return f"{self.BASEURL}/{i1[-1]}/{i1[-2]}/{i1[-3]}/{self.id}.bin"


AccurateRipTrackID1 = int
AccurateRipTrackID2 = int
AccurateRipConfidence = int


# note: tracks are 1-based (first track is track 1)
@dataclass
class AccurateRipResults:
    id: AccurateRipID
    track: Dict[int, Dict[AccurateRipTrackID, AccurateRipConfidence]] = field(init=False)

    def __post_init__(self):
        self.track = {i: {} for i in range(1, self.id.num_tracks+1)}

    # get_item and set_item are 1-based
    def __getitem__(self, track: int) -> Dict[AccurateRipTrackID, AccurateRipConfidence]:
        if track < 1 or track > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track}")
        return self.track[track]

    # get_item and set_item are 1-based
    def __setitem__(self, track, value) -> None:
        if track < 1 or track > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track}")
        self.track[track] = value
        return

    # add_track uses cd track numbers (first track==1)
    def add_track(self, track_no: int, crc1: AccurateRipTrackID1, crc2: AccurateRipTrackID2,
                  confidence: AccurateRipConfidence) -> None:
        if track_no < 1 or track_no > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track_no}")
        track_id = AccurateRipTrackID(crc1, crc2)
        self[track_no][track_id] = confidence
        return

    def find_crc(self, track: int, crc: AccurateRipTrackID) -> Optional[AccurateRipConfidence]:
        try:
            return self[track][crc]
        except KeyError:
            return None


@dataclass(frozen=True)
class AccurateRipTrackID:
    crc1: AccurateRipTrackID1
    crc2: AccurateRipTrackID2

    def __repr__(self) -> str:
        return f"({self.crc1:08x},{self.crc2:08x})"


class AccurateRip:
    #BINARY = PosixPath("/home/bas/NerdProjecten/cdrip/accuraterip/accuraterip")
    BINARY = PosixPath("/home/bas/pycharm/cdrip/accuraterip/accuraterip")

    def __init__(self, disc: cd.Disc, wav_file: PathLike):
        if not self.BINARY.exists():
            raise FileNotFoundError(f"Cannot find accuraterip binary at f{self.BINARY}")
        self._disc = disc
        self._wav = wav_file

    @property
    def offset(self) -> int:
        return self._disc.cdplayer.offset

    @classmethod
    def _run_binary(cls, args: List[str]) -> List[AccurateRipTrackID]:
        result = tools.execcmd(cls.BINARY, args)
        if result.returncode != 0:
            raise AccurateRipException(f"Accuraterip run failed with code {result.returncode}: {result.stderr}")

        # now parse the stdout, expecting output like:
        # track01 03:00:00.000   7938000 435cff30 140a7894
        chksums: List[AccurateRipTrackID] = []
        for line in result.stdout.splitlines():
            (track, _, _, crc1_s, crc2_s) = line.split()
            if not track.startswith("track"):
                raise AccurateRipException(f"Could not parse accuraterip output: \n{result.stdout}")
            crc1 = int(crc1_s, 16)
            crc2 = int(crc2_s, 16)
            chksums.append(AccurateRipTrackID(crc1, crc2))

        return chksums

    def checksum(self, filename: PathLike,
                 sample_start: Optional[int] = None,
                 sample_num: Optional[int] = None) -> AccurateRipTrackID:
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
    def checksum_multi(self, filename: PathLike,
                       tracks: List[Tuple[int, int]], offset: int = 0) -> List[AccurateRipTrackID]:
        if not Path(filename).exists():
            raise FileNotFoundError(f"Audio file '{filename}' not found")

        args = [str(filename)]
        args += ["-o", offset]
        args += ["{}s,{}s".format(*t) for t in tracks]

        chksums = self._run_binary(args)
        return chksums

    def checksum_disc(self) -> List[AccurateRipTrackID]:
        track_spec = [(t.first_sample, t.length_samples) for t in self._disc.tracks]
        chksums = self.checksum_multi(self._wav, track_spec, self.offset)
        print(chksums)
        return [AccurateRipTrackID(0, 0)]

    @staticmethod
    def _parse_accuraterip(bin_data: bytes, orig_id: AccurateRipID) -> AccurateRipResults:
        print(repr(bin_data))

        results = AccurateRipResults(id=orig_id)

        pos = 0
        while pos < len(bin_data):
            accuraterip_id = AccurateRipID(*struct.unpack("<BIII", bin_data[pos:pos+13]))
            if accuraterip_id != orig_id:
                raise AccurateRipException(f"Mismatch in returned accurateripid: {accuraterip_id}!={orig_id}")

            #print(accuraterip_id)
            it = struct.iter_unpack("<BII", bin_data[pos+13:pos+13+9*accuraterip_id.num_tracks])
            for i, track in enumerate(it):
                #print(f" --> {i+1} - {track}")
                results.add_track(i+1, crc1=track[1], crc2=track[2], confidence=track[0])
            pos += 13 + 9 * accuraterip_id.num_tracks

        return results

    def lookup(self) -> Optional[List[AccurateRipTrackID]]:
        accuraterip_id = self._disc.id_accuraterip()

        print(f"Fetching {accuraterip_id.url}")
        response = urllib.request.urlopen(accuraterip_id.url)
        if response.status != 200:
            raise AccurateRipException(f"Couldn't fetch accuraterip entry: {response.reason}")
        ar_known = self._parse_accuraterip(response.read(), accuraterip_id)
        print(ar_known)

        return None
