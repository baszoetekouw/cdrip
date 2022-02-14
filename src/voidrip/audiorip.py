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

#import tocparser
from os import PathLike
from typing import Union, Optional, List
from pathlib import Path

from . import cdplayer
from . import tools


# this class handles the actual ripping from cd to audio file
# all intermediate files are stored as raw 16-bit signed samples (at 44.1kHz)

class AudioRip:
    COMMANDS = {
        'cdrdao': Path('/usr/bin/cdrdao'),
        'cdparanoia': Path('/usr/bin/cdparano1ia'),
        'sox': Path('/usr/bin/sox'),
    }
    sox_raw_spec = ['-t', 'raw', '--endian', 'big',    '-b16', '-esigned', '-c2', '-r44100']
    sox_wav_spec = ['-t', 'wav', '--endian', 'little', '-b16', '-esigned', '-c2', '-r44100']

    def __init__(self, cd : cdplayer.CDPlayer, destdir: PathLike) -> None:
        self._cdplayer: cdplayer.CDPlayer = cd
        self._destdir: Path = Path(destdir)

    @property
    def cd(self) -> cdplayer.CDPlayer:
        return self._cdplayer

    #@property
    #def disc(self) -> Disc:
    #    return self._disc

    @property
    def cwd(self) -> Path:
        return self._destdir

    def path(self, name: Union[PathLike, str]) -> Path:
        return Path(self._destdir, name)

    def rip(self, output) -> None:
        # https://github.com/thomasvs/morituri/blob/master/examples/readdisc.py./con
        pass

    def exec(self, command: str, args: List[str], cwd: Optional[PathLike] = None):
        if cwd is None:
            cwd = self.cwd
        tools.execcmd(self.COMMANDS[command], args, cwd)

    def rip_fast_fullcd(self) -> None:
        # cdrdao
        tools.execcmd(self.COMMANDS['cdrdao'], [
            'read-cd',
            '--datafile', 'cdrdao.raw',
            '--paranoia-mode=2',
            '--device', self.cd.device_name,
            'cdrdao.toc'],
            cwd=self.cwd
        )
        #self._disc = Disc(self.path('cdrdao.toc'), self.path('cdrdao.raw'))

    def rip_accurate_track(self, track: int) -> PathLike:
        # cdparanoia
        outputfile = Path(f'cdparanoia_{track:02d}.wav')
        self.exec('cdparanoia', [
            '--output-wav', '--force-cdrom-device', self.cd.device_name,
            '--sample-offset', f'{self.cd.offset:d}', f'{track:d}',
            outputfile
        ])
        return outputfile

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
