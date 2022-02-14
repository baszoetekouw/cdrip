#
# <one line to give the program's name and a brief idea of what it does.>
# Copyright (C) 2018  Bas Zoetekouw <bas.zoetekouw@surfnet.nl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import musicbrainzngs as mb
import discid
from pprint import pprint

from . import cdplayer


class metadata:
    def __init__(self,device):
        self._useragent = "VoidRippert", "0.1", "bas@zoetekouw.net"
        self._cdplayer = cdplayer.CDPlayer(device)
        self._disc = self._fetch_disc_info()
        self._mb = self._fetch_musicbrainz()
        self._info = self._parse_release_info()

    def _fetch_disc_info(self):
        disc = discid.read(self._cdplayer.device_name(), ['read', 'msn', 'isrc'])
        print("id: %s" % disc.id)
        print("mcn: %s" % disc.mcn)
        print("submission url:\n%s" % disc.submission_url)
        for track in disc.tracks:
            print("{:>2}: {:>4} {:13}".format(track.number,track.seconds,track.isrc))
        return disc

    def _fetch_musicbrainz(self,disc_id,disc_toc):
        mb.set_useragent(self._useragent)

        try:
            # note: adding a toc here will add fuzzy matching, which will return
            # _many_ results
            result = mb.get_releases_by_discid(id=self._disc.id,
                                               includes=["artists","recordings"],
                                               toc=self._disc.toc_string)
        except mb.ResponseError as e:
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
                if 'packaging' not in release:
                    release['packaging']='UNKNOWN'
                print("  {id}: {artist-credit-phrase} / {title} / {medium-count} / {packaging}".format(**release))
            return result['disc']
        elif result.get("cdstub"):
            return result['cdstub']
        elif result.get("release-list"):
            raise NotImplementedError

        # never reached
        raise Exception('Never reached')

    def _parse_release_info(self,mb_disc):
        disc_id = disc['id']

        info = dict()
        info['diskid'] = disc_id

        release = disc['release-list'][0]

        info['artist']   = release['artist-credit-phrase']
        info['title']    = release['title']
        info['date']     = release['date']
        info['disc-tot'] = int(release['medium-count'])

        tracks = None
        for disc in release['medium-list']:
            #if disc['disc-list'][0]['id']==disc_id:
            #if disc_id in [ d['id'] for d in disc['disc-list'] ]:
            disc_ids = map(lambda x: x['id'], disc['disc-list'])
            if disc_id in disc_ids:
                info['disc-num'] = int(disc['position'])
                tracks = [
                    {
                        'num'  : int(t['number']),
                        'pos'  : int(t['position']),
                        'title': t['recording']['title'],
                    }
                    for t in disc['track-list']
                ]
                break

        info['tracks'] = tracks

        return info


    def print_disc_info(self,info):
        print("----")
        print("  Artist: %s" % info['artist'])
        print("  Title:  %s" % info['title'])
        print("  Date:   %s" % info['date'])
        print("  Disc:   %u/%u" % (info['disc-num'],info['disc-tot']))
        print("  Tracks:")
        for track in info['tracks']:
            print("    %(num)02u/%(pos)02u - %(title)s" % track)
        print("----")


