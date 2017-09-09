#!./env/bin/python

import discid
import musicbrainzngs
import pprint
import subprocess
import time
import re
import json
import pyudev
from pprint import pprint

musicbrainzngs.set_useragent("VoidRippert", "0.1", "bas@zoetekouw.net")


# wait until an audio cd is inserted and return the device name
def wait_for_audiocd():
	udev_context = pyudev.Context()
	udev_monitor = pyudev.Monitor.from_netlink(udev_context)
	#udev_monitor.filter_by('cd')
	for dev in iter(udev_monitor.poll, None):
		print("{} ({}): {}".format(dev.device_node, dev.device_type, dev['ACTION']))
		for prop in dev.__iter__():
			print('    {}: {}'.format(prop,dev.get(prop)))
		if 'ID_CDROM_CD' in dev  and  'DISK_MEDIA_CHANGE' in dev  and  'ID_CDROM_MEDIA_CD' in dev:
			return dev.device_node

	return device

def eject(device):
	return
	subprocess.call(['/usr/bin/eject',device])

def fetch_disc_info(devicename):
	disc = discid.read(devicename,['read','msn','isrc'])
	print("id: %s" % disc.id)
	print("mcn: %s" % disc.mcn)
	print("submission url:\n%s" % disc.submission_url)
	for track in disc.tracks:
		print("{:>2}: {:>4} {:13}".format(track.number,track.seconds,track.isrc))
	return disc

def fetch_musicbrainz(disc_id,disc_toc):
	try:
		# note: adding a toc here will add fuzzy matching, which will return
		# _many_ results
		result = musicbrainzngs.get_releases_by_discid(id=disc_id,
				includes=["artists","recordings"]) #,toc=disc_toc)
	except musicbrainzngs.ResponseError as e:
		print("disc not found or bad response")
		pprint(vars(e))
		return None

	#print("--- raw mb:");
	#print(json.dumps(result,indent=2))
	#print("---");


	# three possibilities here: "The result is a dict with either a ‘disc’ , a
	# ‘cdstub’ key or a ‘release-list’ (fuzzy match with TOC). A ‘disc’ has an
	# ‘offset-count’, an ‘offset-list’ and a ‘release-list’. A ‘cdstub’ key
	# has direct ‘artist’ and ‘title’ keys."
	if result.get("disc"):
		print("disc id: %s" % result["disc"]["id"])
		print("Releases:")
		for release in result["disc"]["release-list"]:
			#print(json.dumps(release,indent=4))
			if not 'packaging' in release:
				release['packaging']='UNKNOWN' 
			print("  {id}: {artist-credit-phrase} / {title} / {medium-count} / {packaging}".format(**release))
		return result['disc']
	elif result.get("cdstub"):
		return result['cdstub']
	elif result.get("release-list"):
		raise NotImplementedError

	assert(False) # never reached

def parse_release_info(disc):
	disc_id = disc['id']

	info = dict()
	info['diskid'] = disc_id

	release = disc['release-list'][0]

	info['artist']   = release['artist-credit-phrase']
	info['title']    = release['title']
	info['date']     = release['date']
	info['disc-tot'] = int(release['medium-count'])

	for disc in release['medium-list']:
		#if disc['disc-list'][0]['id']==disc_id:
		if disc_id in [ d['id'] for d in disc['disc-list'] ]:
			info['disc-num'] = int(disc['position'])
			tracks = [ { 
				'num'  : int(t['number']),
				'pos'  : int(t['position']),
				'title': t['recording']['title'],
				} for t in disc['track-list'] 
				]
			break

	info['tracks'] = tracks

	return info


def print_disc_info(info):
	print("----")
	print("  Artist: %s" % info['artist'])
	print("  Title:  %s" % info['title'])
	print("  Date:   %s" % info['date'])
	print("  Disc:   %u/%u" % (info['disc-num'],info['disc-tot']))
	print("  Tracks:")
	for track in info['tracks']:
		print("    %(num)02u/%(pos)02u - %(title)s" % track)
	print("----")



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

	disc_toc=None
	for disc_id in ('2k1hHt5KQPVEiNpm8hIdzqUnYQo-','prJeAorVFSTkgUPo2QKUK_agAIg-','53xaa33729k6Bz5JCNNtRsgydRE-','U_e_qZwjtNytOO9_hW.85msX76U-'):
		release_info = fetch_musicbrainz(disc_id,disc_toc)
		if not release_info:
			print("Disc not found or stub found in Musicbrainz")
			continue
		#pprint.pprint(disc_info)
		disc_info = parse_release_info(release_info)
		print_disc_info(disc_info)
		#eject(devicename)

		print("\n===\n")
		continue

main()
exit(0)
