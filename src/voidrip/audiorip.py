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

import tocparser
from os import PathLike
from typing import Union
from pathlib import Path

from . import cdplayer
from . import tools
from .cd import Disc


# this class handles the actual ripping from cd to audio file

class AudioRip:
	COMMANDS = {
		'cdrdao': '/usr/bin/cdrdao',
		'cdparanoia': '/usr/bin/cdparano1ia',
		'sox': '/usr/bin/sox',
	}

	def __init__(self, cd : cdplayer.CDPlayer, destdir: PathLike) -> None:
		self._cdplayer: cdplayer.CDPlayer = cd
		self._destdir: PathLike = destdir
		self._disc : Disc = Disc()

	@property
	def cd(self):
		return self._cdplayer

	@property
	def disc(self):
		return self._disc

	@property
	def cwd(self):
		return self._destdir

	def path(self, name: Union[PathLike,str]) -> Path:
		return Path(self._destdir, name)

	def rip(self,output):
		# https://github.com/thomasvs/morituri/blob/master/examples/readdisc.py./con
		pass

	def rip_fast_fullcd(self) -> None:
		# cdrdao
		tools.execcmd(
			cmd='cdrdao',
			args=['read-cd', '--datafile', 'cdrdao.raw', '--device', self.cd.devicename, 'cdrdao.toc'],
			cwd=self.cwd
		)
		self.disc.rawfile = self.path('cdrdao.raw')
		self.disc.toc = tocparser.TOC.load(self.path('cdrdao.toc'))

	def rip_accurate_track(self, track: int) -> PathLike:
		# cdparanoia
		outputfile = Path(f'cdparanoia_{track:02d}.wav')
		tools.execcmd('cdparanoia', ['--output-wav', '--force-cdrom-device', self.cd.devicename, '--sample-offset',
		                         f'{self.cd.offset:d}', f'{track:d}', outputfile])
		return outputfile

