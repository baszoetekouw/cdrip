#!./env/bin/python

import pyudev
import voidrip
#from pprint import pprint


# wait until an audio cd is inserted and return the device name
def wait_for_audiocd():
	udev_context = pyudev.Context()
	udev_monitor = pyudev.Monitor.from_netlink(udev_context)
# 	udev_monitor.filter_by('cd')
	for dev in iter(udev_monitor.poll, None):
		print("{} ({}): {}".format(dev.device_node, dev.device_type, dev['ACTION']))
		for prop in dev.__iter__():
			print('    {}: {}'.format(prop, dev.get(prop)))
		if     'ID_CDROM_CD'       in dev \
	       and 'DISK_MEDIA_CHANGE' in dev \
	       and 'ID_CDROM_MEDIA_CD' in dev:
			return dev.device_node

	# never reached



def main():
	#while True:
	#	print("Waiting for cd...")
	#	devicename = wait_for_audiocd()

	#for devicename in ('/dev/cdrom0','/dev/cdrom1','/dev/cdrom2','/dev/cdrom3'):
	#	print("Found cd on device %s" % devicename)
	#	disc = fetch_disc_info(devicename)
	#	if not disc:
	#		print("Couldn't read disc from device `{}'".format(devicename))
	#		continue
	#	disc_id  = disc.id
	#	disc_toc = disc.toc

	ripper = voidrip.Ripper(device='/dev/cdrom',offset=441)
	ripper.start()
	return

	# disc_toc=None
	# for disc_id in ('2k1hHt5KQPVEiNpm8hIdzqUnYQo-','prJeAorVFSTkgUPo2QKUK_agAIg-','53xaa33729k6Bz5JCNNtRsgydRE-','U_e_qZwjtNytOO9_hW.85msX76U-'):
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
