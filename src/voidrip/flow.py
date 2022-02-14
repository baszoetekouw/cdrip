import json
import os
import tempfile
#from pprint import pprint
from os import PathLike
from pathlib import Path
from datetime import datetime
from typing import Optional

from pprint import pprint
from . import cdplayer
from . import cd
from . import audiorip

class CDException(Exception): pass

class VoidRip:
	def __init__(self, device : PathLike = Path('/dev/cdrom'), tmpdir : PathLike = None):
		self._name : str = 'voidrip'
		self._cdplayer : cdplayer = cdplayer.CDPlayer(device)
		self._tmpdir : os.PathLike = tmpdir
		if tmpdir is None:
			self._tempdir = tempfile.TemporaryDirectory(prefix=f'{self._name}_{self._cdplayer.device_name.stem}')
		self._audiorip : audiorip = audiorip.AudioRip(cd=self._cdplayer, destdir=self._tempdir.name)
		self._disc : Optional[cd.Disc] = None

	def get_path(self,filename : str) -> str:
		return os.path.join(self._tempdir.name, filename)

	def start(self) -> None:
		logs = ''
		date_start = datetime.now()

		print("Closing tray")
		self._cdplayer.tray_close()
		if ~self._cdplayer.has_disc():
			print("No disc detected")
			self._cdplayer.tray_open()
			return

		self.fetch_cd_info()

		#self._audiorip.rip_fast_fullcd()
		#self._audiorip.correct_offset()
		#self.check_accuraterip()

		date_finish = datetime.now()
		metdadata = {
			"rip": {
				"ripper": "voidrip",
				"version": "0.1",
				"date": date_finish,
				"rip_duration": date_finish-date_start,
				"stdout": logs
			},
			"cdplayer": self.player_info(),
			"disc": self._disc
		}
		print(json.dumps(metdadata))

		self._cdplayer.tray_open()

	def fetch_cd_info(self):
		if self._disc is None:
			self._disc = self._cdplayer.get_disc()
		pprint(self._disc)

	def player_info(self):
		return self._cdplayer.metadata()

	def check_accuraterip(self):
		# fetch accuraterip cd
		# if found:
		#   calc track checksums
		#   foreach track:
		#     calc track checksum
		#     if not match:
		#       cdrparanoia track
		#       calc track checksum
		#       if not match:
		#         error
		#   if any changed tracks:
		#     write new full disk wav
		pass

