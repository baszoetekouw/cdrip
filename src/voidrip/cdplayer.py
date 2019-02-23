import os
from pathlib import Path
import fcntl
from typing import Union, Tuple, Optional
from os import PathLike
import time

class CDPlayerException(Exception):
	pass


class CDPlayer:
	# from <linux/cdrom.h>
	IOCTL = {
		'CDROM_EJECT'        : 0x5309,
		'CDROM_CLOSETRAY'    : 0x5319,
		'CDROM_DRIVE_STATUS' : 0x5326,
		'CDROM_LOCKDOOR'     : 0x5329
	}

	STATUS = {
		'CDS_NO_INFO'         : 0,
		'CDS_NO_DISC'         : 1,
		'CDS_TRAY_OPEN'       : 2,
		'CDS_DRIVE_NOT_READY' : 3,
		'CDS_DISC_OK'         : 4
	}

	# list read offset _corrections_ (in samples==4 bytes)
	# Positive means: drive reads samples too soon, so samples need to be shifted forwards in time
	# see http://www.accuraterip.com/driveoffsets.htm for the list
	# see https://hydrogenaud.io/index.php/topic,47862.msg425948.html#msg425948 for explanation
	OFFSETS = {
		('PIONEER','DVD-RW  DVR-110D'): 48,
		('Optiarc','DVD RW AD-5260S' ): 48,
		('ATAPI',  'DVD A DH16A6S'   ):  6,
	}

	def __init__(self,device: Union[str,PathLike]='/dev/cdrom') -> None:
		self._device: Path = Path(device)

		# sanity checks
		try:
			self.status()
		except OSError: # open failed
			if not self.device.resolve().is_block_device():
				raise CDPlayerException(f"Device `{self.device}' is not a block device")
			else:
				raise CDPlayerException(f"Can't open device `{self.device}'")

	@property
	def device(self) -> Path:
		return self._device

	@property
	def devicename(self) -> str:
		return os.fspath(self.device)

	@property
	def offset(self) -> int:
		vendor, model = self.get_model()
		#print(f'Found vendor="{vendor}", model="{model}"')
		if vendor is None:
			return 0
		if (vendor,model) in self.OFFSETS:
			#print(f'Found offset={self.OFFSETS[(vendor,model)]}')
			return self.OFFSETS[(vendor,model)]
		else:
			return 0

	def open(self) -> int:
		fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
		return fd

	def ioctl(self, ioctl_id: int, param: int) -> int:
		cdrom = self.open()
		status = fcntl.ioctl(cdrom, ioctl_id, param)
		os.close(cdrom)
		return status

	def status(self) -> int:
		return self.ioctl(CDPlayer.IOCTL['CDROM_DRIVE_STATUS'], 0)

	def is_open(self) -> bool:
		return self.status()==CDPlayer.STATUS['CDS_TRAY_OPEN']

	def has_disc(self) -> bool:
		for i in range(0,15):
			s = self.status()
			if s == CDPlayer.STATUS['CDS_DRIVE_NOT_READY']:
				time.sleep(1)
				continue
			return s==CDPlayer.STATUS['CDS_DISC_OK']
		else:
			raise CDPlayerException("Timeout: Drive not ready")

	def tray_open(self) -> None:
		self.ioctl(CDPlayer.IOCTL['CDROM_LOCKDOOR'], 0)
		self.ioctl(CDPlayer.IOCTL['CDROM_EJECT'], 0)

	def tray_close(self) -> None:
		self.ioctl(CDPlayer.IOCTL['CDROM_LOCKDOOR'], 0)
		self.ioctl(CDPlayer.IOCTL['CDROM_CLOSETRAY'], 0)
		for i in range(0,195):
			if not self.is_open():
				break
			time.sleep(1)
		else:
			raise CDPlayerException('Could not close tray')


	def get_model(self) -> Optional[Tuple[str,str]]:
		fullpath = os.path.realpath(self.device)
		devname = os.path.basename(fullpath)
		syspath = os.path.join('/sys/block', devname, 'device')
		try:
			with open(os.path.join(syspath, 'vendor'), 'r') as f:
				vendor: str = f.readline().rstrip()
			with open(os.path.join(syspath, 'model'), 'r') as f:
				model: str = f.readline().rstrip()
		except OSError:
			raise CDPlayerException(f"Can't open CDplayer sys info in '{syspath}'")
		return vendor, model


