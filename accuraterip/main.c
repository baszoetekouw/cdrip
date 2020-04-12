#include "accuraterip.h"

#include <stdio.h>

int main(const int argc, char **argv)
{
    opts_t options = parse_args(argc,argv);

    soundfile_t soundfile = open_sndfile(options.filename);


    for (unsigned i=0; i<options.num_tracks; i++) {
        track_t track = options.tracks[i];

        const sndbuff_t sndbuf = fill_sndbuf(soundfile, track.sample_start, track.sample_length);

        uint32_t crc_v1 = 0;
        uint32_t crc_v2 = 0;
        int result = accuraterip_checksum(&crc_v1, &crc_v2,
                sndbuf.samples, sndbuf.num_samples, soundfile.info.channels,
                track.is_first_track, track.is_last_track);
        if (result != 0) {
            fprintf(stderr, "Error while calculating checksum\n");
            exit(-1);
        }
        char buf[32];
        printf("track%02u %s %9"PRIu64" %08x %08x\n", i+1,
                samplestostr(buf, sizeof(buf), track.sample_length), track.sample_length,
                crc_v1, crc_v2);

        free(sndbuf.samples);
    }

    close_sndfile(&soundfile);

    return 0;
}

