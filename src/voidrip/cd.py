import collections
import enum
import json
from enum import Enum
from typing import List, Optional, Generator, Dict, Union, Final
#from pathlib import Path

#import tocparser
import pycdio
import cdio
#import discid


# lift tocparser.TOC into our own namespace
#class TOC(tocparser.TOC):
#	pass

# lift tocparser.Track into our own namespace
#class Track(tocparser.Track):
#	pass


class TrackFormat(enum.Enum):
	AUDIO = 'audio'
	MODE1 = 'mode1'
	MODE2 = 'mode2'


class DiscMode(enum.Enum):
	CD_DA      = "CD-DA"
	CD_DATA    = "CD-DATA (Mode 1)"
	CD_XA      = "CD DATA (Mode 2)"
	CD_MIXED   = "CD-ROM Mixed"
	DVD_ROM    = "DVD-ROM"
	DVD_RAM    = "DVD-RAM"
	DVD_R      = "DVD-R"
	DVD_RW     = "DVD-RW"
	HD_DVD_ROM = "HD DVD ROM"
	HD_DVD_RAM = "HD DVD RAM"
	HD_DVD_R   = "HD DVD-R"
	DVD_PR     = "DVD+R"
	DVD_PRW    = "DVD+RW"
	DVD_PRW_DL = "DVD+RW DL"
	DVD_PR_DL  = "DVD+R DL"
	DVD_OTHER  = "Unknown/unclassified DVD"
	NO_INFO    = "No information"
	ERROR      = "Error in getting information"
	CD_I       = "CD-i"


CDText_type = Dict[str, Union[str, Dict]]

# types for cd timings
MSF = collections.namedtuple('MSF', ['min', 'sec', 'frame'])
LBA = int
LSN = int

# basic CD contants
CDA_FRAMES_PER_SEC: Final[int] = 75
CDA_FRAMES_PER_MIN: Final[int] = CDA_FRAMES_PER_SEC * 60
CDA_PREGAP_FRAMES:  Final[int] = 150


def lba2msf(lba: LSN) -> MSF:
	m = lba // CDA_FRAMES_PER_MIN
	lba -= m * CDA_FRAMES_PER_MIN
	s = lba // CDA_FRAMES_PER_SEC
	lba -= s * CDA_FRAMES_PER_SEC
	msf = MSF(min=m, sec=s, frame=lba)
	return msf


def msf2lba(msf: MSF) -> LBA:
	lba = msf.min + msf.sec + msf.frame
	return lba


def lba2lsn(lba: LBA) -> LSN:
	return lba - CDA_PREGAP_FRAMES


def lsn2lba(lsn: LSN) -> LBA:
	return lsn + CDA_PREGAP_FRAMES


class TrackException(Exception):
	pass


class DiscException(Exception):
	pass


class CDJSONEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, bytes):
			try:
				return obj.decode('utf_8')
			except SyntaxError:
				try:
					return obj.decode('iso8859_15')
				except SyntaxError:
					try:
						return obj.decode('utf_16')
					except SyntaxError:
						return ''.join(
							[bytes(b).decode('ASCII') if 32 <= b <= 126 else "?" for b in obj]
						)
		elif isinstance(obj, Track):
			return obj.__dict__
		elif isinstance(obj, Enum):
			return obj.name

		return super(CDJSONEncoder, self).default(obj)


class Track:
	@staticmethod
	def parse_preemphasis(preemphasis: int) -> Optional[bool]:
		if preemphasis == 0:
			return False
		if preemphasis == 1:
			return True
		if preemphasis == 3:
			return None
		raise TrackException(f"Unknown preemphasis value '{preemphasis}'")

	def __init__(self, track: cdio.Track):
		self.num: int = track.track
		self.first_lba: LBA = track.get_lba()
		self.last_lba: LBA = lsn2lba(track.get_last_lsn())
		self.channels: int = track.get_audio_channels()
		self.format: TrackFormat = TrackFormat(track.get_format())
		self.copy_permit: bool = track.get_copy_permit() == 'OK'
		# note: we would use track.get_preemphasis, but it has a bug and doesn't currenty work
		self.preemphasis: Optional[bool] = self.parse_preemphasis(
			pycdio.get_track_preemphasis(track.device, track.track)
		)
		self.is_green: bool = track.is_green()
		self.isrc: str = track.get_isrc()

	def __repr__(self):
		s = f"<{self.__class__.__name__}\n"
		for k, v in {**vars(self), **dict(length=self.length)}.items():
			s += f"  {k}: {v}\n"
		s += ">"
		return s

	@property
	def length(self) -> int:
		return self.last_lba - self.first_lba + 1

	@property
	def start_msf(self) -> MSF:
		return lba2msf(self.first_lba)


class Disc:
	def __init__(self, device: cdio.Device):
		self.first_track: int = pycdio.get_first_track_num(device.cd)
		self.num_tracks: int = pycdio.get_last_track_num(device.cd)
		self.last_track: int = self.first_track + self.num_tracks - 1
		self.tracks: List[Track] = [Track(device.get_track(t)) for t in self.track_nums()]
		self.cdtext: List[CDText_type] = self.parse_cdtext(pycdio.get_cdtext(device.cd))
		self.mcn: Optional[str] = self.get_mcn(device.cd)
		self.mode: DiscMode = DiscMode(pycdio.get_disc_mode(device.cd))
		self.jolietlvl = pycdio.get_joliet_level(device.cd)
		self.verify()

	def __repr__(self) -> str:
		s = ''
		s += f"First track: {self.first_track}\n"
		s += f"Num tracks: {self.num_tracks}\n"
		s += f"MCN: {self.mcn}\n"
		s += f"Mode: {self.mode}\n"
		s += f"Joliet level: {self.jolietlvl}\n"
		s += f"cdtext:"
		s += json.dumps(self.cdtext, indent=4, cls=CDJSONEncoder) + "\n"

		for t in self.tracks:
			s += t.__repr__() + "\n"
		return s

	def as_json(self) -> str:
		return json.dumps(self.__dict__, indent=4, cls=CDJSONEncoder)

	def verify(self) -> None:
		if self.first_track != 1:
			raise DiscException(f"Disc starts with track {self.first_track}.  This is unsupported.")
		if self.mode != DiscMode.CD_DA:
			raise DiscException(f"Disc has mode `{self.mode}'.  This is unsupported.")
		if self.jolietlvl != 0:
			raise DiscException(f"Disc has Joliet level `{self.jolietlvl}'.  This is unsupported.")
		for track in self.tracks:
			if track.format != TrackFormat.AUDIO:
				raise DiscException(f"Found track {track.num} with unsupported mode `{track.format}'")
			if track.channels != 2:
				raise DiscException(f"Found track {track.num} with unsupported numer of channels {track.channels}")
			if track.preemphasis:
				raise DiscException(f"Found track {track.num} with preemphasis.  This is not supported.")
			if track.is_green:
				raise DiscException(f"Found track {track.num} with green=true.  This is not supported.")

	@staticmethod
	def get_mcn(device) -> Optional[str]:
		mcn = pycdio.get_mcn(device)
		if mcn == '0000000000000':
			return None
		return mcn

	# TODO: split out cdtext to its own class
	def parse_cdtext(self, cdtext) -> List[CDText_type]:
		# [ - { language: "<lang>", data: { key: text, ... } ]
		parsed: List[CDText_type] = []
		if cdtext:
			for lang_id in pycdio.cdtext_list_languages_v2(cdtext):
				lang_name = pycdio.cdtext_lang2str(lang_id)
				data: Dict[int, Dict[str, bytes]] = {}
				if lang_id == pycdio.CDTEXT_LANGUAGE_INVALID or lang_id == pycdio.CDTEXT_LANGUAGE_BLOCK_UNUSED:
					continue

				if not pycdio.cdtext_select_language(cdtext, lang_id):
					raise DiscException(f"Could not select language '{lang_name}'")
				for t in [0] + list(self.track_nums()):
					data[t]: Dict[str, bytes] = {}
					for i in range(pycdio.MIN_CDTEXT_FIELD, pycdio.MAX_CDTEXT_FIELDS):
						key = pycdio.cdtext_field2str(i)
						if txt := pycdio.cdtext_get(cdtext, i, t):
							data[t][key] = txt

				parsed.append({"language": lang_name, "data": data})
		return parsed

	def track_nums(self) -> Generator[int, None, None]:
		t = self.first_track
		while t <= self.last_track:
			yield t
			t = t + 1

	def id_cddb(self) -> str:
		return ""

	def id_musicbrainz(self) -> str:
		return ""



#	@property
#	def toc(self) -> TOC:
#		return self._toc

#	@property
#	def discid(self) -> bytes:
#		# scan tracks for min and max number
#		first = min([ t.Number() for t in self.toc.Tracks ])
#		last  = max([ t.Number() for t in self.toc.Tracks ])
#		sectors = self.toc.TotalLength.TotalFrames
#		offsets = [ self.toc.GetTrack(i).FileStart for i in range(first, last+1) ]
#		offsets.append( self.toc.GetTrack(last).FileEnd )
#
#		disc = discid.put(first, last, sectors, offsets)
#		print("id: %s" % disc.id)
#		return disc.id

