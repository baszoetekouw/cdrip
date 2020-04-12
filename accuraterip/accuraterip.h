#ifndef ACCURATERIP_H
#define ACCURATERIP_H

#define bool    _Bool
#define true    1
#define false   0

#define OBSOLETE_IMPLEMENTATIONS 0

#define BYTES_PER_SAMPLE     (4)
#define SAMPLES_PER_FRAME  (588)
#define FRAMES_PER_SECOND   (75)

//#define BYTES_PER_FRAME    (BYTES_PER_SAMPLE*SAMPLES_PER_FRAME)
//#define BYTES_PER_SECOND   (BYTES_PER_FRAME*FRAMES_PER_SECOND)
//#define BYTES_PER_MINUTE   (60*BYTES_PER_SECOND)

#define SAMPLES_PER_SECOND (SAMPLES_PER_FRAME*FRAMES_PER_SECOND)
#define SAMPLES_PER_MINUTE (60*SAMPLES_PER_SECOND)

//#define FRAMES_PER_MINUTE  (60*FRAMES_PER_SECOND)

/* track limit is hard is the spec, but actual CD size/length is implementation/fab dependent,
 * so 99 is a real upper limit, but 85 minutes i simply a practical upper limit */
#define MAX_TRACKS 99
#define MAX_SECONDS (85*60)
#define MAX_SAMPLES (MAX_SECONDS*SAMPLES_PER_SECOND)


#include <inttypes.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <sndfile.h>

extern bool VERBOSE;
#define debug(a...) ({ if (VERBOSE) printf(a); })

typedef struct {
    SNDFILE *fd;
    SF_INFO info;
} soundfile_t;

typedef int16_t sample_t;
typedef int64_t samplenum_t;

typedef struct {
    samplenum_t num_samples;
    sample_t *samples;
} sndbuff_t;

typedef struct {
    samplenum_t sample_start;
    samplenum_t sample_length;
    bool is_first_track;
    bool is_last_track;
} track_t;

typedef struct {
    const char *filename;
    bool test;
    unsigned int num_tracks;
    track_t tracks[MAX_TRACKS];
} opts_t;

/* util.c */
samplenum_t parse_time(const char * const time_str, const size_t buff_size);
const char * samplestostr(char * const buff, const size_t len, const samplenum_t samples);
/* cmdline.c */
int help(const char * const error);
opts_t parse_args(const int argc, char ** argv);
/* file.c */
soundfile_t open_sndfile(const char * const filename);
int close_sndfile(soundfile_t * const soundfile);
sndbuff_t fill_sndbuf(const soundfile_t soundfile,
                      const samplenum_t start, const samplenum_t len);


/* calculate version 1 and version 2 checksum of PCM_s16le data */
int accuraterip_checksum(
    uint32_t * const checksum_v1,
	uint32_t * const checksum_v2,
	const int16_t * const audio_data,
	const size_t num_samples,
	const unsigned short num_channels,
	const bool is_first_track,
	const bool is_last_track);

/* calculate version 1 and version 2 checksum of a subrange in a larger set of PCM_s16le data */
static inline
int __unused accuraterip_checksum_sub(
	uint32_t * const checksum_v1,
	uint32_t * const checksum_v2,
	const int16_t * const audio_data,
	const size_t tot_samples,
	const size_t start_sample,
	const size_t num_samples,
	const unsigned short num_channels,
	const bool is_first_track,
	const bool is_last_track)
{
	assert( num_samples > 0 );
	assert( tot_samples > 0 );
	assert( start_sample < tot_samples );
	assert( start_sample+num_samples <= tot_samples );
	return accuraterip_checksum(
			checksum_v1, checksum_v2,
			audio_data + start_sample*num_channels, num_samples,
			num_channels,
			is_first_track, is_last_track);
}

#endif

