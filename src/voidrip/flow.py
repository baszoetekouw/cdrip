import os
import string
import tempfile
#from pprint import pprint
import discid
from pprint import pprint
from . import cdplayer
from . import cd
from . import audiorip
from .tools import execcmd

class CDException(Exception): pass

class VoidRip:
	def __init__(self, device : string ='/dev/cdrom', tmpdir : os.PathLike = None):
		self._name = 'voidrip'
		self._cdplayer = cdplayer.CDPlayer(device)
		self._tmpdirobj = None
		if tmpdir is None:
			self._tempdirobj = tempfile.TemporaryDirectory(prefix=f'{self._name}_')
			self._tempdir = self._tempdirobj.name
		else:
			self._tempdir = tmpdir
		self._audiorip = audiorip.AudioRip(cd=self._cdplayer, destdir=self._tempdir)
		self._disc = cd.Disc

	def get_path(self,filename : str) -> str:
		return os.path.join(self._tempdir, filename)

	def start(self) -> None:
		print("Closing tray")
		self._cdplayer.tray_close()
		if self._cdplayer.has_disc():
			self.fetch_cd_info()
			#self._audiorip.rip_fast_fullcd()
			self.correct_offset()
			self.check_accuraterip()
			self.fetch_metadata()
		else:
			print("No disc detected")
		self._cdplayer.tray_open()

	def fetch_cd_info(self):
		# calc cddb id
		self._disc = discid.read(device=self._cdplayer.devicename, features=discid.FEATURES_IMPLEMENTED)
		pprint(self._disc)

	def correct_offset(self):
		raw_spec = ['-t', 'raw', '--endian', 'big',    '-b16', '-e', 'signed', '-c2', '-r44100']
		wav_spec = ['-t', 'wav', '--endian', 'little', '-b16', '-e', 'signed', '-c2', '-r44100']

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
		execcmd('sox',raw_spec+['cdrdao.raw', '-t', 'wav', 'cdrdao.wav']+trim_spec, cwd=self._tempdir)

		if self._cdplayer.offset==0:
			# copy wav as-is
			os.link(self.get_path('cdrdao.wav'), self.get_path('cd.wav'))
		else:
			# generate silence
			execcmd('sox',[
				'-t', 's16', '--endian', 'big', '-c2', '-r44100', '/dev/zero',
				'stilte.wav',
				'trim', '0',f'{offset_seconds:.6f}'
			], cwd=self._tempdir)

			if self._cdplayer.offset>0:
				# append silence
				execcmd('sox',['cdrdao.wav','stilte.wav']+wav_spec+['cd.wav'], cwd=self._tempdir)
			else:
				# prepend silence
				execcmd('sox',['stilte.wav','cdrdao.wav']+wav_spec+['cd.wav'], cwd=self._tempdir)

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
