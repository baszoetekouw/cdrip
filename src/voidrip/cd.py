from typing import List
import tocparser
import discid

class Track(discid.Track):
	def __init__(self):
		pass

class Disc:
	def __init__(self):
		self.disc_id: str = None
		self.freedb_id: str = None
		self.msc: str = None
		self.sectors: int = None
		self.toc: tocparser.TOC = None
		self.tracks: List[Track] = None

