#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include <endian.h>
#include <assert.h>

#ifndef ACCURATERIP_H
#define ACCURATERIP_H

/* deprecated functions (use accuraterip_checksum() instead)
 * for a little-endian system, each sample is:
 * struct {
 *   int16_t sample_left;  // little-endian
 *   int16_t sample_right; // little-endian
 * }
 */
uint32_t _accuraterip_checksum_v1_u32(
	const uint32_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track);

uint32_t _accuraterip_checksum_v2_u32(
	const uint32_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track);

/* same as above, but accept an array of individual 16-bit samples (channels should be interleaved) */
static inline
uint32_t _accuraterip_checksum_v1(
	const int16_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track)
{
	assert(__BYTE_ORDER == __LITTLE_ENDIAN);
	const uint32_t * const audio_data_u32 = (const uint32_t * const) audio_data;
	return _accuraterip_checksum_v1_u32(audio_data_u32, audio_num_bytes, is_first_track, is_last_track);
}

static inline
uint32_t _accuraterip_checksum_v2(
	const int16_t * const audio_data,
	const size_t audio_num_bytes,
	const bool is_first_track,
	const bool is_last_track)
{
	assert(__BYTE_ORDER == __LITTLE_ENDIAN);
	const uint32_t * const audio_data_u32 = (const uint32_t * const) audio_data;
	return _accuraterip_checksum_v2_u32(audio_data_u32, audio_num_bytes, is_first_track, is_last_track);
}

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
int accuraterip_checksum_sub(
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
