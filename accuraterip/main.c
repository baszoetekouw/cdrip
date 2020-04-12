#include "accuraterip.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>

#include <sndfile.h>

soundfile_t open_sndfile(const char * const filename)
{
    /* zeroing out the sf_info is required (see sndfile API) */
    soundfile_t soundfile;
    SF_INFO * const info = &soundfile.info;

    memset(info, 0, sizeof(*info));
    soundfile.fd = sf_open(filename, SFM_READ, info);
    if (!soundfile.fd)
    {
        fprintf(stderr, "Can't open file '%s': %s\n", filename, strerror(errno));
        exit(1);
    }

    debug("File opened successfully.\n");
    debug("rate: %i, chan: %i, format: 0x%06x, sect: %i, seek: %i, frames: %"PRId64"\n",
          info->samplerate, info->channels, info->format,
          info->sections, info->seekable, info->frames );

    if ( !(info->format & SF_FORMAT_PCM_16) || info->channels!=2 ) // NOLINT(hicpp-signed-bitwise)
    {
        fprintf(stderr, "This is not a stereo PCM16 file\n");
        exit(1);
    }
    if ( info->samplerate!=44100 )
    {
        fprintf(stderr, "Sample rates other than 44.1kHz are not supported\n");
        exit(1);
    }

    return soundfile;
}

int close_sndfile(soundfile_t * const soundfile)
{
    int ret = sf_close(soundfile->fd);
    soundfile->fd = NULL;
    return ret;
}

sndbuff_t fill_sndbuf(const soundfile_t soundfile,
                            const samplenum_t start, const samplenum_t len)
{
    const SF_INFO * const sf_info = &soundfile.info;
    sndbuff_t sndbuf = {0,NULL};

    /* seek to the starting position */
    /* Note: seek uses 2-channel samples, so seek of 1 means skip 32 bits */
    if (sf_seek(soundfile.fd, start, SEEK_SET)<0)
    {
        fprintf(stderr, "Error while seeking to sample %"PRId64"\n", start);
        exit(1);
    }

    /* Note: 1 sample consists of 2 16-bit values (left and right channel) */
    if (len>0)
        sndbuf.num_samples = len;
    else
        sndbuf.num_samples = sf_info->frames - start;

    size_t buf_size = sndbuf.num_samples * sf_info->channels * sizeof(int16_t);
    sndbuf.samples  = malloc(buf_size);

    /* just to make sure the buffer really get filled correctly and to make debugging easier*/
    memset(sndbuf.samples,0xff, buf_size);
    debug("buf size: %zu\n", buf_size);

    long num_read = sf_read_short(soundfile.fd, sndbuf.samples, sndbuf.num_samples * sf_info->channels);
    debug("read %lli samples\n", sndbuf.num_samples);

#if 0
    for (uint8_t *p = (uint8_t*) buf; p<(uint8_t*)buf+buf_size; p++)
        printf("%s%02x",((void*)p-(void*)buf)%40==0?"\n":" ",*p);
    printf("\n");
#endif

    if (num_read != sndbuf.num_samples * sf_info->channels)
    {
        fprintf(stderr, "Could read only %li of %"PRId64" frames\n", num_read, sf_info->frames);
        exit(1);
    }

    return sndbuf;
}

int main(const int argc, char **argv)
{
    opts_t options = parse_args(argc,argv);

    soundfile_t soundfile = open_sndfile(options.filename);

    const sndbuff_t sndbuf = fill_sndbuf(soundfile, options.tracks[0].sample_start, options.tracks[0].sample_length);

    close_sndfile(&soundfile);

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
		int result1 = accuraterip_checksum(&crc_v1b, &crc_v2b, buf, num_samples, sf_info.channels, false, false);
		int result2 = accuraterip_checksum(&crc_v1c, &crc_v2c, buf, num_samples, sf_info.channels, true,  false);
		int result3 = accuraterip_checksum(&crc_v1d, &crc_v2d, buf, num_samples, sf_info.channels, false, true);
		int result4 = accuraterip_checksum(&crc_v1e, &crc_v2e, buf, num_samples, sf_info.channels, true,  true);
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
        int result = accuraterip_checksum(&crc_v1, &crc_v2, sndbuf.samples, sndbuf.num_samples,
                soundfile.info.channels, options.tracks[0].is_first_track, options.tracks[0].is_last_track);
        if (result!=0)
        {
            fprintf(stderr,"Error while calculating checksum\n");
            exit(-1);
        }
        printf("%08x\n%08x\n", crc_v1, crc_v2);
    }

    free(sndbuf.samples);

    return 0;
}

