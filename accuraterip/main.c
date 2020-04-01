#include "accuraterip.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>

#include <sndfile.h>

int main(const int argc, char **argv)
{
    opts_t options = parse_args(argc,argv);

    SF_INFO info;
    memset(&info,0,sizeof(info));
    SNDFILE *fd = sf_open(options.filename, SFM_READ, &info);
    if (!fd)
    {
        fprintf(stderr,"Can't open file '%s': %s\n",options.filename,strerror(errno));
        exit(1);
    }
    debug("File opened succesfully.\n");
    debug("rate: %i, chan: %i, format: 0x%06x, sect: %i, seek: %i, frames: %"PRId64"\n",
            info.samplerate, info.channels, info.format, info.sections, info.seekable, info.frames );

    if ( !(info.format & SF_FORMAT_PCM_16) || info.channels!=2 ) // NOLINT(hicpp-signed-bitwise)
    {
        fprintf(stderr, "This is not a stereo PCM16 file\n");
        exit(1);
    }
    if ( info.samplerate!=44100 )
    {
        fprintf(stderr, "Samplerates other than 44.1kHz are not supported\n");
        exit(1);
    }

    /* seek to the starting position */
    /* Note: seek uses 2-channel samples, so seek of 1 means skip 32 bits */
    if (sf_seek(fd,options.tracks[0].sample_start,SEEK_SET)<0)
    {
        fprintf(stderr, "Error while seeking to sample %"PRId64"\n", options.tracks[0].sample_start);
        exit(1);
    }

    /* Note: 1 sample consists of 2 16-bit values (left and right channel) */
    sample_t num_samples;
    if (options.tracks[0].sample_length>0)
        num_samples = options.tracks[0].sample_length;
    else
        num_samples = info.frames-options.tracks[0].sample_start;

    size_t buf_size = num_samples * info.channels * sizeof(int16_t);
    int16_t * buf  = malloc(buf_size);
    memset(buf,0xff,buf_size);
    debug("buf size: %zu\n", buf_size);

    long num_read = sf_read_short(fd, buf, num_samples*info.channels);
    debug("read %li samples\n", num_read);

    //for (uint8_t *p = (uint8_t*) buf; p<(uint8_t*)buf+buf_size; p++) printf("%s%02x",((void*)p-(void*)buf)%40==0?"\n":" ",*p);
    //printf("\n");

    if (num_read!=num_samples*info.channels)
    {
        fprintf(stderr, "Could read only %li of %"PRId64" frames\n", num_read, info.frames);
        exit(1);
    }

    sf_close(fd);

#if OBSOLETE_IMPLEMENTATIONS
    /* test mode calculates all different variations */
	if (options.test) {
		/* now calc checksums */
		uint32_t crc_v1a = _accuraterip_checksum_v1(buf, buf_size, false, false);
		uint32_t crc_v2a = _accuraterip_checksum_v2(buf, buf_size, false, false);

		uint32_t crc_v1b = 0;
		uint32_t crc_v2b = 0;
		uint32_t crc_v1c = 0;
		uint32_t crc_v2c = 0;
		uint32_t crc_v1d = 0;
		uint32_t crc_v2d = 0;
		uint32_t crc_v1e = 0;
		uint32_t crc_v2e = 0;
		int result1 = accuraterip_checksum(&crc_v1b, &crc_v2b, buf, num_samples, info.channels, false, false);
		int result2 = accuraterip_checksum(&crc_v1c, &crc_v2c, buf, num_samples, info.channels, true,  false);
		int result3 = accuraterip_checksum(&crc_v1d, &crc_v2d, buf, num_samples, info.channels, false, true);
		int result4 = accuraterip_checksum(&crc_v1e, &crc_v2e, buf, num_samples, info.channels, true,  true);
		if (result1!=0 || result2!=0 || result3!=0 || result4!=0)
		{
			fprintf(stderr,"Error while calculating checksum\n");
			exit(-1);
		}

		printf("checksums:\n");
		printf(" - v1a: %08x - v2a: %08x\n", crc_v1a, crc_v2a);
		printf(" - v1b: %08x - v2b: %08x\n", crc_v1b, crc_v2b);
		printf("\n");
		printf("checksum v1: n: %08x, f: %08x, l: %08x, s: %08x\n", crc_v1b, crc_v1c, crc_v1d, crc_v1e);
		printf("checksum v2: n: %08x, f: %08x, l: %08x, s: %08x\n", crc_v2b, crc_v2c, crc_v2d, crc_v2e);
	}
	/* normal mode only outputs version 1 and version 2 checksums */
	else
#endif
    {
        uint32_t crc_v1 = 0;
        uint32_t crc_v2 = 0;
        int result = accuraterip_checksum(&crc_v1, &crc_v2, buf, num_samples, info.channels,
                                          options.tracks[0].is_first_track, options.tracks[0].is_last_track);
        if (result!=0)
        {
            fprintf(stderr,"Error while calculating checksum\n");
            exit(-1);
        }
        printf("%08x\n%08x\n", crc_v1, crc_v2);
    }

    free(buf);

    return 0;
}

