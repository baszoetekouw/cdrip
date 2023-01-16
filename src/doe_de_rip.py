#!./env/bin/python

from __future__ import annotations

# import pyudev
import sys
# import time
# import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pprint import pprint
from typing import Optional, List
import csv
import readline  # for input

import filelock

import voidrip
from pathlib import Path

# from os import PathLike
# from pprint import pprint
from voidrip import cd


@dataclass
class Options:
    cdrom: Path


readline.read_init_file()


def parse_args() -> Options:
    if len(sys.argv) < 2:
        print("Please specify cdrom number")
        sys.exit(1)
    try:
        num = int(sys.argv[1])
    except ValueError:
        print("Please specify the cdrom number (0<=n<5)")
        sys.exit(1)

    return Options(
        cdrom=Path(f"/dev/cdrom{num}")
    )


class RipStatusCode(Enum):
    INITIALIZING = 1
    RIPPING      = 2
    RIP_DONE     = 3
    METADATA     = 4
    DONE         = 5


class RipStatus:
    dir = {
        RipStatusCode.RIPPING:  Path("/data/cdrip/work/1_ripping"),
        RipStatusCode.RIP_DONE: Path("/data/cdrip/work/2_ripdone"),
        RipStatusCode.METADATA: Path("/data/cdrip/work/3_metadata"),
        RipStatusCode.DONE:     Path("/data/cdrip/work/4_done"),
        "status": Path("/data/cdrip/status")
    }

    def __init__(self, cdplayer: voidrip.CDPlayer):
        for p in self.dir.values():
            p.mkdir(parents=True, exist_ok=True)
        self._id: int = self.register_next_id()
        self._work_dir = self.create_dir_phase1(cdplayer.device_name)

        self.write_statusfile(status=RipStatusCode.INITIALIZING)

    @staticmethod
    def id_to_name(id_num: int) -> Path:
        return Path(f"cd_{id_num:05d}")

    def register_next_id(self) -> int:
        num = 1
        while True:
            filename = self.dir["status"] / self.id_to_name(num).with_suffix(".status")
            try:
                with open(filename, "x") as statusfile:
                    statusfile.write("")
                return num
            except FileExistsError:
                num += 1
                continue

    def create_dir_phase1(self, cdrom_path: Path) -> Path:
        work_dir = self.dir[RipStatusCode.RIPPING] / cdrom_path.name / Path(f"{datetime.now():%Y%m%d_%H%M%S}")
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> Path:
        return self.id_to_name(self._id)

    @property
    def status_file(self) -> Path:
        return self.dir["status"] / self.name.with_suffix(".status")

    def read_statusfile(self) -> tuple[RipStatusCode, Optional[str], Optional[str]]:
        try:
            with open(self.status_file, "r") as statusfile:
                s = statusfile.readline().rstrip()
                status = RipStatusCode[s] if s else None
                artist = statusfile.readline().rstrip()
                album = statusfile.readline().rstrip()
        except ValueError:
            raise Exception(f"Invalid status '{s}' in {self.status_file}")

        if artist == '':
            artist = None
        if album == '':
            album = None

        return status, artist, album

    def write_statusfile(self, status: Optional[RipStatusCode] = None,
                         artist: Optional[str] = None, album: Optional[str] = None) -> None:
        try:
            old_status, old_artist, old_album = self.read_statusfile()
        except FileNotFoundError:
            old_status, old_artist, old_album = (RipStatusCode.INITIALIZING, None, None)

        new_status = status if status else old_status
        new_artist = artist if artist else old_artist
        new_album  = album  if album  else old_album

        with open(self.status_file, "w") as statusfile:
            print(new_status.name, file=statusfile)
            print(new_artist if new_artist else '', file=statusfile)
            print(new_album  if new_album  else '', file=statusfile)

        return

    @property
    def status(self) -> RipStatusCode:
        status, _, _ = self.read_statusfile()
        return status

    @status.setter
    def status(self, status: RipStatusCode) -> None:
        self.write_statusfile(status=status)

    def get_artist_album(self) -> tuple[Optional[str], Optional[str]]:
        _, artist, album = self.read_statusfile()
        return artist, album

    def set_artist_album(self, artist: Optional[str] = None, album: Optional[str] = None) -> None:
        self.write_statusfile(artist=artist, album=album)

    @property
    def work_dir_phase1(self):
        if self._work_dir is None:
            raise Exception("Work dir not initialized")
        return self._work_dir

    @property
    def id_file(self) -> Path:
        return self.dir["status"] / "disc_ids.txt"

    def find_duplicates(self, disc: cd.Disc) -> Optional[List[str]]:
        with filelock.FileLock(str(self.id_file.with_name(".lock"))):
            try:
                with open(self.id_file) as fd:
                    csvfile = csv.reader(fd, delimiter=" ")
                    #results = [f[0] for f in fd.readline().split(None, 2) if f[1] == disc.id_musicbrainz()]
                    #bla = [(f[0],f[1]) for f in csvfile ]

                    results = [f[0] for f in csvfile if f[1] == disc.id_musicbrainz()]
            except FileNotFoundError:
                results = []

            if not results:
                with open(self.id_file, "a") as f:
                    print(f"{self.name} {disc.id_musicbrainz()}", file=f)
                return None
        return results

    def save_id(self, disc: cd.Disc) -> None:
        with filelock.FileLock(str(self.id_file.with_name(".lock"))):
            with open(self.id_file, "a") as f:
                print(f"{self.name} {disc.id_musicbrainz()}", file=f)
        return None


def input_yes_no(prompt: str, default=True) -> bool:
    answer = input(prompt)
    if len(answer) == 0:
        return default
    first = answer.lower()[0]
    if first == 'y' or first == 'j':
        return True
    if first == 'n':
        return False
    return default


def rip_cd(options: Options) -> None:
    print(f"using cdrom {options.cdrom}")

    cdplayer = voidrip.CDPlayer(options.cdrom)
    cdplayer.tray_open()

    input("Insert CD and press Enter...")
    cdplayer.tray_close()

    print("Waiting for cd...")
    cdplayer.wait_for_disc()
    print("Found media")

    rip_status = RipStatus(cdplayer)
    print(f"CD rip will have number {rip_status.id}")

    print("Reading TOC")
    disc = cdplayer.get_disc()
    pprint(disc)

    print("Looking for duplicates...", end="")
    if duplicates := rip_status.find_duplicates(disc):
        print(f"\nThis disc seems to have been ripped already as {','.join(duplicates)}")
        answer = input_yes_no("Do you wish to continue? (no) ", default=False)
        if not answer:
            return
    else:
        print("none found")
    rip_status.save_id(disc)

    artist, album = disc.get_performer_title()
    if artist and album:
        answer = input_yes_no(f"CD claims to be `{album}` by `{artist}`, is that correct? (yes) ", default=True)
        if not answer:
            artist, album = (None, None)
    # get user input, if necessary
    if not (artist and album):
        print("Please input Artist and Album title manually; this will not be used in actual metadata.")
        artist = input("Artist: ")
        album = input("Album title: ")
    rip_status.set_artist_album(artist=artist, album=album)

    print("Starting rip")
    rip = voidrip.AudioRipper(disc, rip_status.work_dir_phase1)
    rip.rip()

    print("Rip done")
    rip.save(rip_status.dir[RipStatusCode.RIP_DONE], rip_status.name)

    print(rip.as_json())
    cdplayer.tray_open()

    return


def main():
    options = parse_args()

    while True:
        rip_cd(options)

    # return


if __name__ == '__main__':
    main()
    exit(0)
