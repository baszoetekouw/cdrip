#!/usr/bin/env python3.4

import discid
import musicbrainzngs
import pprint
import subprocess
import time
import re

musicbrainzngs.set_useragent("VoidRippert", "0.1", "bas@zoetekouw.net")


# wait until an audio cd is inserted and return the device name
def wait_for_audiocd():
	r = re.compile(r"\A\*\*\*DiskAppeared \('(.+?)'.* DAVolumeKind = '(.+?)'")

	# read output from "diskutil activity" until we see a cddafs filesystem
	# appearing
	p = subprocess.Popen(['/usr/sbin/diskutil','activity'],
	      bufsize=1,stdout=subprocess.PIPE,universal_newlines=True)
	f = p.stdout
	device = None
	while not device:
		while not f.readable(): 
			time.sleep(0.1)
		while f.readable():
			l = f.readline()
			match = r.match(l)
			if match:
				if match.group(2)=='cddafs':
					device = match.group(1)
					break;
	p.terminate()
	return device

def eject(device):
	subprocess.call(['/usr/sbin/diskutil','eject',device])

def fetch_disc_info():
	disc = discid.read()
	try:
		result = musicbrainzngs.get_releases_by_discid(disc.id, 
				includes=["artists","recordings"])
	except musicbrainzngs.ResponseError:
		print("disc not found or bad response")
		return None
	else:
		print("disc id: %s" % result["disc"]["id"])
		print("release: %s" % result["disc"]["release-list"][0]["id"])
	
		if result.get("disc"):
			return result['disc']
		elif result.get("cdstub"):
			return result['cdstub']
		return None

def parse_disc_info(disc):
	discid = disc['id']

	info = dict()
	info['diskid'] = discid

	release = disc['release-list'][0]

	info['artist']   = release['artist-credit-phrase']
	info['title']    = release['title']
	info['date']     = release['date']
	info['disc-tot'] = release['medium-count']

	for disc in release['medium-list']:
		#if disc['disc-list'][0]['id']==discid:
		if discid in [ d['id'] for d in disc['disc-list'] ]:
			info['disc-num'] = disc['position']
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
	print("===============================")
	print("Artist: %s" % info['artist'])
	print("Title:  %s" % info['title'])
	print("Date:   %s" % info['date'])
	print("#discs: %u" % info['disc-tot'])
	print("Tracks:")
	for track in info['tracks']:
		print("  %(num)02u/%(pos)02u - %(title)s" % track)
	print("===============================")



def main():
	while True:
		print("Waiting for cd...")
		devicename = wait_for_audiocd()
		print("Found cd on device %s" % devicename)
		disc_info = fetch_disc_info()
		if not disc_info:
			print("Disc not found or stub found in Musicbrainz")
			continue
		#pprint.pprint(disc_info)
		disc_info = parse_disc_info(disc_info)
		print_disc_info(disc_info)
		eject(devicename)

		break

main()
exit(0)
