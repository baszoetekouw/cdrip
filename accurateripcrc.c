#include <stdint.h>
#include <assert.h>

#define BYTES_PER_SECTOR   (2352)                         /* number of bytes per sector */
#define BYTES_PER_SAMPLE   (sizeof(uit32_t))              /* number of bytes per sample */
#define SAMPLES_PER_SECTOR (BYTES_PER_SECTOR/SAMPLE_SIZE) /* number of samples per sector */

uint32_t compute_v1_checksum(
	const uint32_t const * audio_data,
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
		p += 5*SAMPLES_PER_SECTOR;
	}
	/* skip last 5 seconds in final track */
	if (is_last_track)
	{
		audio_num_samples -= 5*SAMPLES_PER_SECTOR;
	}

	uint32_t crc     = 0;
	uint32_t crc_pos = 1;
	for (; p < audio_num_samples; p++)
	{
		crc += crc_pos++ * (*p);
	}

	return crc;
}

uint32_t compute_v2_checksum(
	const uint32_t const * audio_data,
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
		p += 5*SAMPLES_PER_SECTOR;
	}
	/* skip last 5 seconds in final track */
	if (is_last_track)
	{
		audio_num_samples -= 5*SAMPLES_PER_SECTOR;
	}

    uint32_t crc     = 0;
	uint64_t crc_pos = 1;
	for (; p < audio_num_samples; p++)
	{
		const uint64_t crc_tmp = crc_pos++ * (*p);
		const uint32_t crc_tmp_hi = (uint32_t)( CalcCRCNEW >> 32 );
		const uint32_t crc_tmp_lo = (uint32_t)( CalcCRCNEW & (uint64_t)0xffffffff );
		crc += crc_tmp_hi + crc_tmp_lo;
	}

	return crc;
}

