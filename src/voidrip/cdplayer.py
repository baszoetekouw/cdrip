import os
from pathlib import Path
import fcntl
from typing import Tuple, Optional, Dict, List, Any
from os import PathLike
#import enum
import time
import pyudev
import yaml

from . import tools
from . import cd
from .cd import Track

# todo: replace low-level ioctls by udev calls or cdio
import cdio
#import pycdio

class CDPlayerException(Exception):
	pass


def msn(lsn: int) -> str:
	blk_per_sec = 75
	sam_per_sec = 44100
	sam_per_blk = sam_per_sec/blk_per_sec
	sam_per_min = blk_per_sec*60

	minute = lsn // sam_per_min
	lsn -= minute * sam_per_min

	second = lsn // sam_per_sec
	lsn -= second * sam_per_sec

	block = lsn // sam_per_blk
	lsn -= block * sam_per_blk

	return f"{minute:02u}:{second:02u}:{block:02u}.{lsn:03u}"


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
		('PIONEER', 'DVD-RW  DVR-110D'):  48,
		('Optiarc', 'DVD RW AD-5260S' ):  48,
		('ATAPI',   'DVD A DH16A6S'   ):   6,
		('hp',      'DVD_A_DH16AESH'  ):   6,
		('hp',      'DVD-RAM GH40L'   ): 667,
		('HL-DT-ST','DVDRAM GH24NSD1' ):   6
	}



	def __init__(self, device: PathLike='/dev/cdrom') -> None:
		self._dev_path: Path = Path(device).resolve()
		self._udev_context: pyudev.Context = pyudev.Context()
		self._udev_device: pyudev.Device = pyudev.Devices.from_device_file(self._udev_context, str(self._dev_path))

		self._device: cdio.Device = cdio.Device(str(self._dev_path))
		self._cdinfo = None

		# sanity checks
		try:
			self.status()
		except OSError: # open failed
			if not self.device.resolve().is_block_device():
				raise CDPlayerException(f"Device `{self.device}' is not a block device")
			else:
				raise CDPlayerException(f"Can't open device `{self.device}'")

	def metadata(self) -> Dict:
		return {
			"device": self.device.name,
			"model": self.get_model(),
			"offset": self.offset
		}

	@property
	def device(self) -> Path:
		return self._dev_path

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
			raise CDPlayerException("Unknown drive; unable to get drive offset")

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
		if self._udev_device.properties.get('ID_CDROM_MEDIA_CD'):
			return True
		return False

		#for i in range(0,15):
		#	s = self.status()
		#	if s == CDPlayer.STATUS['CDS_DRIVE_NOT_READY']:
		#		time.sleep(1)
		#		continue
		#	return s==CDPlayer.STATUS['CDS_DISC_OK']
		#else:
		#	raise CDPlayerException("Timeout: Drive not ready")

	def wait_for_disc(self) -> None:
		if self.has_disc():
			return

		# wait until an audio cd is inserted and return the device name
		udev_monitor = pyudev.Monitor.from_netlink(self._udev_context)
		udev_monitor.filter_by('block')
		for dev in iter(udev_monitor.poll, None):
			#print(f"Notify for {dev.device_node} {type(dev.device_node)}")
			if self._dev_path == Path(dev.device_node) \
			   and dev.properties.get('DISK_MEDIA_CHANGE') \
			   and dev.properties.get('ID_CDROM_MEDIA_CD'):
					return

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

	def get_drive_info(self) -> Dict[str,str]:
		model, vendor = self.get_model()
		return dict(
			model = model,
			vendor = vendor,
			offset = self.offset,
		)

	@property
	def firsttrack(self):
		track_first = self._device.get_first_track().track
		if track_first!=1:
			raise CDPlayerException(f"First track is not 1 but `{track_first}'")
		return track_first

	@property
	def lasttrack(self):
		return self._device.get_last_track().track

	@property
	def tracks(self):
		return list(range(self.firsttrack, self.lasttrack+1))

	def get_tracks(self) -> List[Track]:
		tracks = []
		for t in self.tracks:
			try:
				track = self._device.get_track(t)
			except:
				raise CDPlayerException(f"Failed to fetch track {t}")
			tracks.append(Track(track))
		return tracks

	@property
	def info(self) -> Dict[str,Any]:
		if self._cdinfo is None:
			yml = tools.execcmd(Path(tools.script_dir().parent,"cd-info","cd-info"), [str(self._dev_path)]).stdout
			self._cdinfo = yaml.safe_load(yml)
		return self._cdinfo

	def get_disc_mcn(self) -> Optional[str]:
		mcn = self._device.get_mcn()
		return mcn if mcn else None

	def get_track_info(self, track_num: int) -> Track:
		track = self._device.get_track(track_num)
		return Track(track)


	def get_disc(self) -> cd.Disc:
		disc = cd.Disc(self._device)
		return disc



