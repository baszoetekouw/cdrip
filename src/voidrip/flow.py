from pprint import pprint
import os
import pathlib
import fcntl
import tempfile
import subprocess
import discid


class VoidRip:
	def __init__(self,device='/dev/cdrom',offset=0):
		self._name = 'voidrip'
		self._device = device
		self._offset = offset
		self._tempdir = tempfile.TemporaryDirectory(prefix=f'{self._name}_')
		self._commands = {
			'cdrdao':     '/usr/bin/cdrdao',
			'cdparanoia': '/usr/bin/cdparanoia',
			'sox':        '/usr/bin/sox',
		}
		self._disc = None
		pass

	def run(self,cmd,args=()):
		bin = self._commands[cmd]
		cmdline = [bin] + list(args)
		print(f'Running: "{cmdline}"')
		oldpwd = os.getcwd()
		os.chdir(self._tempdir.name)
		subprocess.run(cmdline)
		os.chdir(oldpwd)

	def get_path(self,filename):
		return os.path.join(self._tempdir.name,filename)

	def start(self):
		self.fetch_cd_info()
		self.rip_audio_fast()
		self.correct_offset()
		self.check_accuraterip()
		self.fetch_metadata()

	def fetch_cd_info(self):
		# calc cddb id
		self._disc = discid.read(device=self._device,features=discid.FEATURES_IMPLEMENTED)

	def rip_audio_fast(self):
		# cdrdao
		self.run('cdrdao', ['read_cd', '--datafile', 'cdrdao.raw', '--device', self._device, 'cdrdao.toc'])
		with open(self.get_path('cdrdao.toc'), 'r') as f:
			print(f.read())

	def correct_offset(self):
		raw_spec = ['-t raw', '--endian big',    '-b 16', '-e signed', '-c 2', '-r 44100']
		wav_spec = ['-t wav', '--endian little', '-b 16', '-e signed', '-c 2', '-r 44100']

		# calculate offset in seconds
		# let's just hope the offset is always <60 seconds
		offset_time = abs(self._offset/44100)

		# wav conversion
		trim_spec = []
		if self._offset>0:
			trim_spec = ['trim',f'{offset_time:.6f}']
		elif self._offset<0:
			trim_spec = ['trim','0',f'-{offset_time:.6f}']
		self.run('sox',raw_spec+['cdrdao.raw', '-t wav', 'cdrdao.wav']+trim_spec)

		if self._offset==0:
			os.link(self.get_path('cdrdao.wav'), self.get_path('cd.wav'))
		else:
			# generate silence
			self.run('sox',[
				'-t','s16','--endian','big', '-c2', '-r44100', '/dev/zero',
				'stilte.wav',
				'trim', '0',f'{offset_time:.6f}'
			])

			if self._offset>0:
				# append silence
				self.run('sox',['cdrdao.wav','stilte.wav']+wav_spec+['cd.wav'])
			else:
				# prepend silence
				self.run('sox',['stilte.wav','cdrdao.wav']+wav_spec+['cd.wav'])

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
