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

import tempfile
import os
import tocparser
from os import PathLike
from typing import Union
from pathlib import Path

from . import cdplayer
from . import tools


# this class handles the actual ripping from cd to audio file

class AudioRip:
	def __init__(self,cd : cdplayer.CDPlayer,tmpdir: tempfile.TemporaryDirectory=None):
		self._cd: cdplayer.CDPlayer = cd
		self._tmpdir: tempfile.TemporaryDirectory = tmpdir
		self._commands = {
			'cdrdao':     '/usr/bin/cdrdao',
			'cdparanoia': '/usr/bin/cdparano1ia',
			'sox':        '/usr/bin/sox',
		}
		pass

	def path(self, name: Union[PathLike,str]):
		return os.path.join(self._tmpdir.name,[name])

	def rip(self,output):
		# https://github.com/thomasvs/morituri/blob/master/examples/readdisc.py./con
		pass

	def rip_fast_fullcd(self) -> None:
		# cdrdao
		tools.execcmd(
			cmd='cdrdao',
			args=['read_cd', '--datafile', 'cdrdao.raw', '--device', self._cd.device(), 'cdrdao.toc'],
			cwd=self._tmpdir
		)
		toc = tocparser.TOC.load(self.path('cdrdao.toc'))
		print(toc)

	def rip_accurate_track(self, track: int) -> PathLike:
		# cdparanoia
		outputfile = Path(f'cdparanoia_{track:02d}.wav')
		tools.execcmd('cdparanoia', ['--output-wav', '--force-cdrom-device', self._cd.device(), '--sample-offset',
		                         f'{self._cd.offset():d}', f'{track:d}', outputfile])
		return outputfile

