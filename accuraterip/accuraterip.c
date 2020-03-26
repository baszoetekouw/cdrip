#include <stdint.h>
#include <assert.h>

#include <stdio.h>

#include "accuraterip.h"

#define HI_U64(x) ((uint32_t)((x)>>32U))
#define LO_U64(x) ((uint32_t)((x)&(uint64_t)0xffffffff))

/* keeping this for reference's sake.  Doesn't properly calculate checksums for first or last track.
 * Please use accuraterip_checkum() instead
 */
# if OBSOLETE_IMPLEMENTATIONS
uint32_t _accuraterip_checksum_v1_u32(
	const uint32_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track)
{
	assert( audio_num_bytes % BYTES_PER_SAMPLE == 0 );
	assert( audio_num_bytes < UINT32_MAX            );

	const uint32_t *p = audio_data;  /* current pos in audio sample data */
	uint32_t audio_num_samples = audio_num_bytes / BYTES_PER_SAMPLE;

	/* skip first 5 frames in first track */
	if (is_first_track)
	{
		//p += 5*SAMPLES_PER_FRAME;
		assert(0); /* not supported */
	}
	/* skip last 5 seconds in final track */
	if (is_last_track)
	{
		audio_num_samples -= 5*SAMPLES_PER_FRAME;
	}

	uint32_t crc_pos = 1;
	uint32_t crc     = 0;
	for (; p < audio_data+audio_num_samples; p++)
	{
		//printf("num: %zu, pos: %u, sample: %08x, crc: %u\n", p-audio_data, crc_pos, (*p), crc);
		crc += crc_pos++ * (*p);
	}

	return crc;
}
#endif

/* keeping this for reference's sake.  Doesn't properly calculate checksums for first or last track.
 * Please use accuraterip_checkum() instead
 */
#if OBSOLETE_IMPLEMENTATIONS
uint32_t _accuraterip_checksum_v2_u32(
	const uint32_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track)
{
	assert( audio_num_bytes % BYTES_PER_SAMPLE == 0 );
	assert( audio_num_bytes < UINT32_MAX            );

	const uint32_t *p = audio_data;  /* current pos in audio sample data */
	uint32_t audio_num_samples = audio_num_bytes / BYTES_PER_SAMPLE;

	/* skip first 5 seconds in first track */
	if (is_first_track)
	{
		// p += 5*SAMPLES_PER_FRAME;
		assert(0); /* not supported */
	}
	/* skip last 5 seconds in final track */
	if (is_last_track)
	{
		audio_num_samples -= 5*SAMPLES_PER_FRAME;
	}

	uint64_t crc_pos = 1;
    uint32_t crc     = 0;
	for (; p < audio_data+audio_num_samples; p++)
	{
		const uint64_t crc_tmp = crc_pos++ * (*p);
		const uint32_t crc_tmp_hi = (uint32_t)( crc_tmp >> 32 );
		const uint32_t crc_tmp_lo = (uint32_t)( crc_tmp & (uint64_t)0xffffffff );
		crc += crc_tmp_hi + crc_tmp_lo;
	}

	return crc;
}
#endif

int accuraterip_checksum(
	uint32_t * const checksum_v1,
	uint32_t * const checksum_v2,
	const int16_t * const audio_data,
	const size_t num_samples,
	const unsigned short num_channels,
	const bool is_first_track,
	const bool is_last_track)
{
	assert( num_samples > 0 );
	assert( audio_data );
	assert( num_samples < 0xffffffffUL );
	if (num_channels!=2)
	{
		fprintf(stderr,"Only 2-channel audio is supported\n");
		return -1;
	}

	/* skip first 5 seconds in first track and last 5 seconds in final track */
	const uint16_t *audio_start = (const uint16_t *) audio_data;
	const uint16_t *audio_end   = audio_start + num_samples*num_channels;
	uint32_t crc_pos = 1;
	if (is_first_track)
	{
		/* not sure why you would want to skip 5 full sectors minus 1 sample.  Maybe an off-by-one in
		 * the original implementation?
		 */
		audio_start += (5*SAMPLES_PER_FRAME-1)*num_channels;
		crc_pos += 5*SAMPLES_PER_FRAME-1;
		//printf("starting at pos %td, crc_pos=%u\n", (void*)audio_start-(void*)audio_data, crc_pos);
	}
	if (is_last_track)
	{
		/* a the the end, we do skip exactly 5 full sectors */
		audio_end -= 5*SAMPLES_PER_FRAME*num_channels;
	}

	uint32_t crc1    = 0;
	uint32_t crc2    = 0;
	for (const uint16_t *p = audio_start; p < audio_end; p+=2, crc_pos++)
	{
		const uint32_t left  = (uint16_t) *p;      /* left channel  */
		const uint32_t right = (uint16_t) *(p+1);  /* right channel */
		const uint32_t val   = (right<<16U) | left; /* combined left/right in a single sample */

		/* checksums are calculated by adding all sample values together, with a multiplication
		 * factor, and letting it overflow happily */
		const uint64_t tmp = (uint64_t) val * crc_pos;

		/* this will creepily overflow, but that's how it supposed to be, I guess */
		crc1 += tmp;

		/* version 2 handles the overflow a little bit more explicitly.  Not sure if it's actually better... */
		crc2 += HI_U64(tmp) + LO_U64(tmp);
	}

	*checksum_v1 = crc1;
	*checksum_v2 = crc2;

	return 0;
}

