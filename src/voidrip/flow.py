import os
import string
import tempfile
#from pprint import pprint
import discid
from . import cdplayer
from . import cd
from . import audiorip
from .tools import execcmd

class CDException(Exception): pass

class VoidRip:
	def __init__(self,device : string ='/dev/cdrom',offset : int = 0):
		self._name = 'voidrip'
		self._cdplayer = cdplayer.CDPlayer(device,offset)
		self._tempdir = tempfile.TemporaryDirectory(prefix=f'{self._name}_')
		self._audiorip = audiorip.AudioRip(cd=self._cdplayer)
		self._disc = cd.Disc

		pass

	def get_path(self,filename):
		return os.path.join(self._tempdir.name,filename)

	def start(self):
		self._cdplayer.tray_close()
		if self._cdplayer.has_disc():
			self._cdplayer.tray_open()
			self.fetch_cd_info()
			self._audiorip.rip_fast_fullcd()
			self.correct_offset()
			self.check_accuraterip()
			self.fetch_metadata()
		self._cdplayer.tray_open()

	def fetch_cd_info(self):
		# calc cddb id
		self._disc = discid.read(device=self._cdplayer.device(), features=discid.FEATURES_IMPLEMENTED)

	def correct_offset(self):
		raw_spec = ['-t raw', '--endian big',    '-b 16', '-e signed', '-c 2', '-r 44100']
		wav_spec = ['-t wav', '--endian little', '-b 16', '-e signed', '-c 2', '-r 44100']

		# calculate offset in seconds
		# let's just hope the offset is always <60 seconds
		offset_seconds = abs(self._cdplayer.offset/44100)
		if offset_seconds>=60:
			raise NotImplementedError("Offsets >60s are not supported")

		# wav conversion
		trim_spec = []
		if self._cdplayer.offset>0:
			trim_spec = ['trim',f'{offset_seconds:.6f}']
		elif self._cdplayer.offset<0:
			trim_spec = ['trim','0',f'-{offset_seconds:.6f}']
		execcmd('sox',raw_spec+['cdrdao.raw', '-t wav', 'cdrdao.wav']+trim_spec)

		if self._cdplayer.offset==0:
			# copy wav as-is
			os.link(self.get_path('cdrdao.wav'), self.get_path('cd.wav'))
		else:
			# generate silence
			execcmd('sox',[
				'-t','s16','--endian','big', '-c2', '-r44100', '/dev/zero',
				'stilte.wav',
				'trim', '0',f'{offset_seconds:.6f}'
			])

			if self._cdplayer.offset>0:
				# append silence
				execcmd('sox',['cdrdao.wav','stilte.wav']+wav_spec+['cd.wav'])
			else:
				# prepend silence
				execcmd('sox',['stilte.wav','cdrdao.wav']+wav_spec+['cd.wav'])

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

	def fetch_metadata(self):
		# fetch metadata from musicbrainz
		# if found 1 match:
		#   use match
		# elif found >1 match:
		#   show results to use, ask choice
		# elif found stub:
		#   show stub url
		# elif not found:
		#   ask for artist/title/year
		#   submit stub
		#   show stub url
		# save metadata in metadata file
		pass
