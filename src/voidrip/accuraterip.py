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
from pathlib import PosixPath
from typing import Dict, Tuple, Optional, List

import audiotools
import audiotools.accuraterip

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
        extra = {
            "id": self.id
        }
        return self.__dict__ | extra

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
        self.track = {i: {} for i in range(1, self.id.num_tracks + 1)}

    @classmethod
    def parse_accuraterip_bin(cls, bin_data: bytes, orig_id: AccurateRipID) -> AccurateRipResults:
        # print(repr(bin_data))

        results = cls(id=orig_id)

        pos = 0
        while pos < len(bin_data):
            accuraterip_id = AccurateRipID(*struct.unpack("<BIII", bin_data[pos:pos + 13]))
            if accuraterip_id != orig_id:
                raise AccurateRipException(f"Mismatch in returned accurateripid: {accuraterip_id}!={orig_id}")

            # print(accuraterip_id)
            it = struct.iter_unpack("<BII", bin_data[pos + 13:pos + 13 + 9 * accuraterip_id.num_tracks])
            for i, track in enumerate(it):
                # print(f" --> {i+1} - {track}")
                results.add_track(i + 1, crc1=track[1], crc2=track[2], confidence=track[0])
            pos += 13 + 9 * accuraterip_id.num_tracks

        return results

    def __repr__(self) -> str:
        ret = ""
        ret += f"{type(self).__name__}(id={self.id},"
        for t, values in self.track.items():
            ret += f"\n    track {t:02d}: "
            ret += "\n              ".join([f"{k}: {v}" for k, v in values.items()])
        ret += ")"
        return ret

    # get_item and set_item are 1-based
    def __getitem__(self, track: cd.TrackNr) -> Dict[AccurateRipTrackID, AccurateRipConfidence]:
        if track < 1 or track > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track}")
        return self.track[track]

    # get_item and set_item are 1-based
    def __setitem__(self, track, value: Dict[AccurateRipTrackID, AccurateRipConfidence]) -> None:
        if track < 1 or track > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track}")
        self.track[track] = value
        return

    # add_track uses cd track numbers (first track==1)
    def add_track(self, track_no: cd.TrackNr, crc1: AccurateRipTrackID1, crc2: AccurateRipTrackID2,
                  confidence: AccurateRipConfidence
                  ) -> None:
        if track_no < 1 or track_no > self.id.num_tracks:
            raise AccurateRipException(f"Invalid track number {track_no}")
        track_id = AccurateRipTrackID(crc1, crc2)
        self[track_no][track_id] = confidence
        return

    def get_track_crc1(self, track_no: cd.TrackNr) -> List[Tuple[AccurateRipTrackID1, AccurateRipConfidence]]:
        crcs = [(ar_id.crc1, confidence) for ar_id, confidence in self.__getitem__(track_no).items()]
        return sorted(crcs, key=lambda x: x[1], reverse=True)

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
    # BINARY = PosixPath("/home/bas/NerdProjecten/cdrip/accuraterip/accuraterip")
    BINARY = PosixPath("/home/bas/pycharm/cdrip/accuraterip/accuraterip")
    PREVIOUS_TRACK_FRAMES = (5880 // 2)
    NEXT_TRACK_FRAMES = (5880 // 2)

    def __init__(self, disc: cd.Disc, wav_file: PathLike):
        self._ar_results: Optional[AccurateRipResults] = None
        if not self.BINARY.exists():
            raise FileNotFoundError(f"Cannot find accuraterip binary at f{self.BINARY}")
        self._disc = disc
        self._wav = wav_file

    @property
    def offset(self) -> int:
        return self._disc.cdplayer.offset

    @property
    def ar_results(self) -> Optional[AccurateRipResults]:
        if self._ar_results is None:
            self.ar_lookup()
        return self._ar_results

    def checksum_disc(self) -> Dict[cd.TrackNr, Dict[AccurateRipConfidence, AccurateRipTrackID1]]:
        return self.checksum_disc_audiotools()

    def checksum_track(self, track: cd.Track) -> Dict[int, AccurateRipTrackID1]:
        return self._checksum_track_audiotools(track)

    def _checksum_track_audiotools(self, track: cd.Track) -> Dict[int, AccurateRipTrackID1]:
        file = audiotools.open(self._wav)
        # just doublechecking
        if not isinstance(file, audiotools.WaveAudio) \
           or not file.supports_to_pcm() \
           or file.channels() != 2 \
           or file.sample_rate() != cd.CDA_SAMLES_PER_SEC \
           or file.bits_per_sample() != cd.CDA_BITS_PER_SAMPLE:
            raise AccurateRipException("Input file doesn't look like a CDA rip")

        # most of this is taken from https://github.com/tuffy/python-audio-tools/blob/master/trackverify#L244
        reader = file.to_pcm()
        if not hasattr(reader, "seek") or not callable(reader.seek):
            raise AccurateRipException("Can't seek in file")

        # we start reading a bit before the track, in order to try out different offsets for the accuraterip checksums
        # the reader below will take care of padding if this is negative
        offset = track.first_sample - self.PREVIOUS_TRACK_FRAMES

        if offset > 0:
            offset -= reader.seek(offset)

        checksummer = audiotools.accuraterip.Checksum(
            total_pcm_frames=track.length_samples,
            sample_rate=cd.CDA_SAMLES_PER_SEC,
            is_first=track.is_first,
            is_last=track.is_last,
            pcm_frame_range=self.PREVIOUS_TRACK_FRAMES + 1 + self.NEXT_TRACK_FRAMES,
            accurateripv2_offset=self.PREVIOUS_TRACK_FRAMES
        )

        window_reader = audiotools.PCMReaderWindow(
            reader, offset,
            self.PREVIOUS_TRACK_FRAMES + track.length_samples + self.NEXT_TRACK_FRAMES
        )

        audiotools.transfer_data(window_reader.read, checksummer.update)

        checksums_v1 = checksummer.checksums_v1()

        crc1_by_offset: Dict[int, AccurateRipTrackID1] = {
            i: AccurateRipTrackID1(c) for i, c in enumerate(checksums_v1, -self.PREVIOUS_TRACK_FRAMES)
        }

        return crc1_by_offset

    def checksum_disc_audiotools(self) -> Dict[cd.TrackNr, Dict[AccurateRipConfidence, AccurateRipTrackID1]]:
        results_by_track = {t.num: self.checksum_track(track=t) for t in self._disc.tracks}
        return results_by_track

    def ar_lookup(self) -> None:
        accuraterip_id = self._disc.id_accuraterip()

        #print(f"Fetching {accuraterip_id.url}")
        print("  Looking up disc in accuraterip database... ", end='')
        response = urllib.request.urlopen(accuraterip_id.url)
        if response.status == 200:
            print("found!")
            self._ar_results = AccurateRipResults.parse_accuraterip_bin(response.read(), accuraterip_id)
        elif response.status == 404:
            print("not found :(")
            self._ar_results = None
        else:
            raise AccurateRipException(f"Couldn't fetch accuraterip entry: {response.status}: {response.reason}")

    def find_confidence_track(self, track: cd.TrackNr) -> Tuple[AccurateRipConfidence, int]:
        # list of (crc1,confidence) tuples
        ar_crcs = self.ar_results.get_track_crc1(track)
        # dict of {offset: crc1} pairs
        track_crcs = self.checksum_track(self._disc.tracks[track-1])

        for ar_crc1, confidence in ar_crcs:
            for offset, track_crc in track_crcs.items():
                if ar_crc1 == track_crc:
                    return confidence, offset

        return 0, 0

    def find_confidence(self) -> Optional[Dict[cd.TrackNr, AccurateRipConfidence]]:
        print("Matching disc with Acucuraterip database...")

        if self.ar_results is None:
            print("No accuraterip results found for disc")
            return None

        confidences: Dict[cd.TrackNr, AccurateRipConfidence] = dict()
        for t in self._disc.track_nums():
            confidence, offset = self.find_confidence_track(t)
            confidences[t] = confidence

            print(f"  - Track {t:-2d}: ", end="")
            if confidence > 0:
                print(f"found matching crc at offset {offset} with confidence {confidence}")
            else:
                print(f"no matching crc found for track {t}")

        return confidences
