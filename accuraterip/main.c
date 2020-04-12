#include "accuraterip.h"

#include <stdio.h>

int main(const int argc, char **argv)
{
    opts_t options = parse_args(argc,argv);

    soundfile_t soundfile = open_sndfile(options.filename);

    const sndbuff_t sndbuf = fill_sndbuf(soundfile, options.tracks[0].sample_start, options.tracks[0].sample_length);

    close_sndfile(&soundfile);

    uint32_t crc_v1 = 0;
    uint32_t crc_v2 = 0;
    int result = accuraterip_checksum(&crc_v1, &crc_v2, sndbuf.samples, sndbuf.num_samples,
            soundfile.info.channels, options.tracks[0].is_first_track, options.tracks[0].is_last_track);
    if (result!=0)
    {
        fprintf(stderr,"Error while calculating checksum\n");
        exit(-1);
    }
    printf("%08x\n%08x\n", crc_v1, crc_v2);

    free(sndbuf.samples);

    return 0;
}

