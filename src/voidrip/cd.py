from typing import List
from pathlib import Path
import tocparser
import discid

class Track(discid.Track):
	def __init__(self):
		pass



class Disc:
	def __init__(self):
		# Musicbrainz disc_id
		self.disc_id: str = None
		# FreeDB disc id
		self.freedb_id: str = None
		# on-disc MSC
		self.msc: str = None
		# number of sectors on disc
		self.sectors: int = None
		# TOC as read by cdrdao
		self._toc: tocparser.TOC = None
		# filename of the raw audio disc dump
		self.rawfile: Path = None
		# list of tracks
		self.tracks: List[Track] = None

	@property
	def toc(self):
		return self._toc

	@toc.setter
	def toc(self, toc):
		self._toc = toc
		#TODO: fill tracks from TOC
