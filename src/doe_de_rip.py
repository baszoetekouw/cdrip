#!./env/bin/python

#import pyudev
#import sys
#import time
#import json
import voidrip
from pathlib import Path
#from os import PathLike
#from pprint import pprint

cdrom_dev = Path("/dev/cdrom1")


def main():
	cdplayer = voidrip.CDPlayer(cdrom_dev)
	#cdplayer.tray_open()
	#time.sleep(1.0)

	print("Waiting for cd...")
	cdplayer.wait_for_disc()

	print("Found media")

	#info = cdplayer.info
	#print(json.dumps(info, sort_keys=True, indent=4))

	disc = cdplayer.get_disc()
	print(disc.as_json())
	print("cddb_id: ", disc.id_cddb())
	print("musicbrainz_id: ", disc.id_musicbrainz())
	return


	#for devicename in ('/dev/cdrom0','/dev/cdrom1','/dev/cdrom2','/dev/cdrom3'):
	#	print("Found cd on device %s" % devicename)
	#	disc = fetch_disc_info(devicename)
	#	if not disc:
	#		print("Couldn't read disc from device `{}'".format(devicename))
	#		continue
	#	disc_id  = disc.id
	#	disc_toc = disc.toc

	#ripper = voidrip.Ripper(device='/dev/cdrom1', tmpdir=Path('/tmp/cdtest'))
	#ripper.start()
	#return

	# disc_toc=None
	# for disc_id in ('2k1hHt5KQPVEiNpm8hIdzqUnYQo-','prJeAorVFSTkgUPo2QKUK_agAIg-',
	#                 '53xaa33729k6Bz5JCNNtRsgydRE-','U_e_qZwjtNytOO9_hW.85msX76U-'):
	# 	release_info = voidrip.rip.fetch_musicbrainz(disc_id,disc_toc)
	# 	if not release_info:
	# 		print("Disc not found or stub found in Musicbrainz")
	# 		continue
	# 	#pprint.pprint(disc_info)
	# 	disc_info = voidrip.rip.parse_release_info(release_info)
	# 	voidrip.rip.print_disc_info(disc_info)
	# 	#eject(devicename)
	#
	# 	print("\n===\n")
	# 	continue

main()
exit(0)
