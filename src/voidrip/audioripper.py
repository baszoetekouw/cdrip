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

from __future__ import annotations

#import tocparser
import json
import subprocess
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from os import PathLike, system
import os.path
from typing import Union, Optional, List
from pathlib import Path

import pytz

from . import cd
from . import cdplayer
from .accuraterip import AccurateRip
from . import tools


class AudioRipperException(Exception):
    pass


# this class handles the actual ripping from cd to audio file
# all intermediate files are stored as raw 16-bit signed samples (at 44.1kHz)
class AudioRipper:
    COMMANDS = {
        'cdrdao': Path('/usr/bin/cdrdao'),
        'icedax': Path('/usr/bin/icedax'),
        'cdparanoia': Path('/usr/bin/cdparano1ia'),
        'sox': Path('/usr/bin/sox'),
        'flac': Path('/usr/bin/flac')
    }
    sox_raw_spec = ['-t', 'raw', '--endian', 'little', '-b16', '-esigned', '-c2', '-r44100']
    sox_wav_spec = ['-t', 'wav', '--endian', 'little', '-b16', '-esigned', '-c2', '-r44100']

    def __init__(self, disc : cd.Disc, destdir: PathLike) -> None:
        self.disc: cd.Disc = disc
        self.cdplayer: cdplayer.CDPlayer = disc.cdplayer
        self.destdir: Path = Path(destdir)
        self.wav_file: Optional[Path] = None
        self.flac_file: Optional[Path] = None
        self.rip_date: datetime = datetime.now(pytz.timezone("Europe/Amsterdam")).replace(microsecond=0)

        self.destdir.mkdir(parents=True, exist_ok=True)

    def as_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, cls=tools.AudioRipperJSONEncoder)

    @property
    def cd(self) -> cdplayer.CDPlayer:
        return self.cdplayer

    @property
    def cwd(self) -> Path:
        return self.destdir

    def path(self, name: Union[PathLike, str]) -> Path:
        return Path(self.destdir, name)

    def rip(self) -> None:
        self.wav_file = self.rip_icedax()
        accuraterip = AccurateRip(self.disc, self.wav_file)
        confidence = accuraterip.find_confidence()
        if confidence is not None:
            for track, conf in [(t, c) for t, c in confidence.items() if c < 10]:
                print(accuraterip.ar_results)
                print(f"Track {track} failed (confidence is {conf}, retrying")
                raise AudioRipperException("Reripping tracks is not implemented yet")
        self.flac_file = self.convert_to_flac()

        return

    def exec(self, command: str, args: List[str], cwd: Optional[PathLike] = None):
        if cwd is None:
            cwd = self.cwd
        cmd = self.COMMANDS[command]
        process = tools.execcmd(cmd=cmd, args=args, cwd=cwd, show_output=True)
        if process.returncode != 0:
            print(f"Woops, command '{cmd}' failed:")
            print(process.stderr)
            process.check_returncode()
        print(process.stdout)
        print(process.stderr)

    def rip_icedax(self) -> PathLike:
        output_file = self.path('icedax.wav')

        if output_file.exists():
            print("Rip exists, skipping")
            return output_file

        args = [
            self.COMMANDS['icedax'],
            '-D', self.cd.device_name,
            '--max', '--no-infofile',
            '--output-format', 'wav',
            '--track', f"{self.cd.firsttrack}+{self.cd.lasttrack}",
            output_file
        ]

        print("Ripping disc using icedax:")

        popen = Popen(args, cwd=self.cwd,
                      stdout=PIPE, stderr=STDOUT, encoding='ascii', text=True, bufsize=0)

        # produce some fancy output
        current_track = 0
        while popen.poll() is None:
            line = popen.stdout.readline().rstrip()

            if current_track > 0:
                if "%" in line:
                    print(f"\rTrack {current_track:-2d}/{self.cd.lasttrack}: {line}", end="")
                if "recorded successfully" in line:
                    print()

            if line == 'percent_done:' or line.endswith("recorded successfully"):
                current_track += 1

        if popen.returncode != 0:
            print("Error while ripping, cleaning up")
            output_file.unlink(missing_ok=True)

        return output_file

    def convert_to_flac(self) -> PathLike:
        input_file = self.wav_file
        output_file = self.path("icedax.flac")

        output_file.unlink(missing_ok=True)
        if output_file.exists():
            print("Flac exists, skipping")
            return output_file

        args = [
            self.COMMANDS['flac'],
            "--no-keep-foreign-metadata",
            "-6",
            "--output-name=" + str(output_file),
            input_file
        ]

        print("Converting image to flac")

        popen = Popen(args, cwd=self.cwd,
                      stdout=PIPE, stderr=STDOUT, encoding='ascii', text=True, bufsize=0)
        #subprocess.run(args)

        # produce some fancy output
        while popen.poll() is None:
            chars = popen.stdout.read(8)
            print(chars, end='')

        if popen.returncode != 0:
            print("Error while ripping, cleaning up")
            output_file.unlink(missing_ok=True)

        return output_file

    def rip_accurate_track(self, track: int) -> PathLike:
        # cdparanoia
        outputfile = Path(f'cdparanoia_{track:02d}.wav')
        self.exec('cdparanoia', [
            '--output-wav', '--force-cdrom-device', self.cd.device_name,
            '--sample-offset', f'{self.cd.offset:d}', f'{track:d}',
            outputfile
        ])
        return outputfile

    def convert_to_wav(self) -> PathLike:
        filename = 'cdrdao.wav'
        if os.path.exists(self.path(filename)):
            print("Wav exists, skipping")
        else:
            self.exec('sox',
                      self.sox_raw_spec + ['cdrdao.raw'] +
                      self.sox_wav_spec + [filename]
                      )
        self.wav_file = self.path(filename)
        return self.wav_file

    def correct_offset(self):
        # examples:
        #   add 294 samples at the start: sox new.wav padded1.wav  trim 0 -294s  pad 294s 0
        #   add 294 samples at the end:   sox new.wav padded2.wav  trim    294s  pad 0 294s

        # Positive correction means: drive reads samples too soon, so samples need to be shifted
        # forwards in time
        correction = self.cd.offset
        if correction > 0:
            trim_spec = ['trim', '0', f'-{correction}s',     'pad', f'{correction}s', '0']
        elif correction < 0:
            trim_spec = ['trim',      f'{abs(correction)}s', 'pad', '0', f'{correction}s']
        else:
            trim_spec = []

        self.exec('sox',
                  self.sox_raw_spec + ['cdrdao.raw'] +
                  self.sox_raw_spec + ['cdrdao_shifted.raw'] +
                  trim_spec
                  )
