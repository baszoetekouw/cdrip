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

import filelock

import voidrip
from pathlib import Path

# from os import PathLike
# from pprint import pprint
from voidrip import cd


@dataclass
class Options:
    cdrom: Path


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
        self._status : RipStatusCode = RipStatusCode.INITIALIZING
        self._work_dir = self.create_dir_phase1(cdplayer.device_name)

    @staticmethod
    def id_to_name(id_num: int) -> Path:
        return Path(f"cd_{id_num:05d}")

    def register_next_id(self) -> int:
        num = 1
        while True:
            filename = self.dir["status"] / self.id_to_name(num).with_suffix(".status")
            try:
                with open(filename, "x") as statusfile:
                    statusfile.write(RipStatusCode.INITIALIZING.name)
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
        return self.dir["status"] / self.name

    @property
    def status(self) -> RipStatusCode:
        with open(self.status_file, "r") as statusfile:
            s = statusfile.readline().rstrip()
            try:
                return RipStatusCode(s)
            except ValueError:
                raise Exception(f"Invalid status '{s}' in {self.status_file}")

    @status.setter
    def status(self, status: RipStatusCode) -> None:
        with open(self.status_file, "x") as statusfile:
            statusfile.write(status.name)

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

    print("Looking for duplicates...", end="")
    if duplicates := rip_status.find_duplicates(disc):
        print(f"\nThis disc seems to have been ripped already as {','.join(duplicates)}")
        answer = input("Do you wish to continue?")
        if answer.lower().startswith("n"):
            return
    else:
        print("none found")
    rip_status.save_id(disc)

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

    return


if __name__ == '__main__':
    main()
    exit(0)
