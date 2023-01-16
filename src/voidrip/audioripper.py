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

import json
import os
import os.path
from datetime import datetime
from os import PathLike
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from typing import Union, Optional, List, Dict

import pytz

from . import cd
from . import cdplayer
from . import tools
from .accuraterip import AccurateRip, AccurateRipConfidence


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
        self.accuraterip_results: Optional[Dict[cd.TrackNr, AccurateRipConfidence]] = None

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
        self.accuraterip_results = confidence
        self.flac_file = self.convert_to_flac()

        return

    def save(self, dest: Path, basename: Path) -> None:
        if not dest.is_dir():
            raise AudioRipperException(f"Destination '{dir}' for save is not a directory")
        if list(dest.glob(str(basename)+"*")):
            raise AudioRipperException(f"Destination id '{dest / basename}' already exists")

        name = dest / basename
        self.wav_file.rename(name.with_suffix(".flac"))
        with open(name.with_suffix(".json"), "x") as fp:
            fp.write(self.as_json())

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

        print("Converting sound to flac")

        popen = Popen(args, cwd=self.cwd,
                      stdout=PIPE, stderr=STDOUT, encoding='ascii', text=True, bufsize=0)

        # produce some fancy output
        # flac produces annoying output, including a non-removable preamble.
        # and a progress indicator that overwrites itself by backspacing over the old text
        # like this:
        # ╰─▶ flac -6 --output-name=icedax.flac -f cdrdao.wav|& xxd
        # 00000000: 0a66 6c61 6320 312e 342e 320a 436f 7079  .flac 1.4.2.Copy
        # 00000010: 7269 6768 7420 2843 2920 3230 3030 2d32  right (C) 2000-2
        # 00000020: 3030 3920 204a 6f73 6820 436f 616c 736f  009  Josh Coalso
        # 00000030: 6e2c 2032 3031 312d 3230 3232 2020 5869  n, 2011-2022  Xi
        # 00000040: 7068 2e4f 7267 2046 6f75 6e64 6174 696f  ph.Org Foundatio
        # 00000050: 6e0a 666c 6163 2063 6f6d 6573 2077 6974  n.flac comes wit
        # 00000060: 6820 4142 534f 4c55 5445 4c59 204e 4f20  h ABSOLUTELY NO
        # 00000070: 5741 5252 414e 5459 2e20 2054 6869 7320  WARRANTY.  This
        # 00000080: 6973 2066 7265 6520 736f 6674 7761 7265  is free software
        # 00000090: 2c20 616e 6420 796f 7520 6172 650a 7765  , and you are.we
        # 000000a0: 6c63 6f6d 6520 746f 2072 6564 6973 7472  lcome to redistr
        # 000000b0: 6962 7574 6520 6974 2075 6e64 6572 2063  ibute it under c
        # 000000c0: 6572 7461 696e 2063 6f6e 6469 7469 6f6e  ertain condition
        # 000000d0: 732e 2020 5479 7065 2060 666c 6163 2720  s.  Type `flac'
        # 000000e0: 666f 7220 6465 7461 696c 732e 0a0a 6364  for details...cd
        # 000000f0: 7264 616f 2e77 6176 3a20 3125 2063 6f6d  rdao.wav: 1% com
        # 00000100: 706c 6574 652c 2072 6174 696f 3d31 2e30  plete, ratio=1.0
        # 00000110: 3033 0808 0808 0808 0808 0808 0808 0808  03..............
        # 00000120: 0808 0808 0808 0808 0808 3225 2063 6f6d  ..........2% com
        # 00000130: 706c 6574 652c 2072 6174 696f 3d31 2e30  plete, ratio=1.0
        #
        # parse this, so we only output "\r34% complete"
        buf = ""
        output_enable = False
        while popen.poll() is None:
            # make sure to read less than 1 line per iteration here.
            buf += popen.stdout.read(32)

            # remove preamble
            if buf.find(": ") > 0:
                _, _, buf = buf.partition(": ")
                output_enable = True

            if output_enable:
                # make sure we don't end with backspace, because then the partition won't work
                if buf.rfind("\b") != len(buf):
                    line, _, buf = buf.rpartition("\b")
                    # note that line cannot be multple lines because we read less than a full line per iteration
                    if line:
                        line = line.strip(" \b")
                        print(f"\r{line}", end="", flush=True)

        print()

        if popen.returncode != 0:
        # if result.returncode != 0:
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
