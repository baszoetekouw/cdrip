#include "accuraterip.h"

#include <errno.h>

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
        fprintf(stderr, "format=0x%x, channels=%u\n", info->format, info->channels);
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
    if (ret==0)
        memset(soundfile, 0, sizeof(*soundfile));
    return ret;
}

UNUSED
sndbuff_t fill_sndbuf(const soundfile_t soundfile,
                      const samplenum_t start, const samplenum_t len)
{
    return fill_sndbuf_offset(soundfile, start, len, 0);
}


/* read samples from file and put them in a newly allocated buffer
 * if offset is non-zero, shift all samples backward in the buffer
 * by either inserting 0s at the start of the buffer, or by skipping the
 * correct amount of sample at start or end
 */
sndbuff_t fill_sndbuf_offset(const soundfile_t soundfile,
                             const samplenum_t start, const samplenum_t len,
                             const samplenum_t offset)
{
    const SF_INFO * const sf_info = &soundfile.info;
    sndbuff_t sndbuf = {0,NULL};

    assert(sf_info->channels==2);
    assert(sf_info->format && SF_FORMAT_PCM_16);

    /* Note: 1 sample consists of 2 16-bit values (left and right channel) */
    if (len>0)
        sndbuf.num_samples = len;
    else
        sndbuf.num_samples = sf_info->frames - start;

    size_t buf_size = sndbuf.num_samples * BYTES_PER_SAMPLE;
    sndbuf.samples  = malloc(buf_size);
    if (sndbuf.samples==NULL) {
        fprintf(stderr, "Failed to allocate %zu bytes\n", buf_size);
        exit(1);
    }

    /* just to make sure the buffer really get filled correctly and to make debugging easier*/
    memset(sndbuf.samples, 0xff, buf_size);
    debug("buf size: %zu\n", buf_size);

    /* handle the case that start+offset or start+len+offset is outside the available samples in soundfile
     * this either occurs at the first track if offset is negative, or at the last track if
     * offset is positive */
    /* positive offset means the drive reads sample too soon, so samples need to be shifted backwards and
     * padding needs to be inserted at the beginning */
    sample_t *buf_read_start = sndbuf.samples;
    samplenum_t read_start = start-offset;            /* position in file to start reading */
    samplenum_t read_len = sndbuf.num_samples; /* number of samples to read from file */
    if (read_start < 0) {
        samplenum_t padding = llabs(read_start);
        assert(padding>0);
        memset(buf_read_start, 0, padding * BYTES_PER_SAMPLE);
        buf_read_start += padding * sf_info->channels;
        read_len -= padding;
        read_start = 0;
    }
    if (read_start+read_len > sf_info->frames ) { /* note: read_start includes offset */
        samplenum_t padding = (read_start+read_len) - sf_info->frames;
        assert(padding>0);
        sample_t *buf_end = sndbuf.samples + sndbuf.num_samples * sf_info->channels;
        memset(buf_end-padding*sf_info->channels, 0, padding*BYTES_PER_SAMPLE);
        read_len -= padding;
    }

    /* seek to the starting position */
    /* Note: seek uses 2-channel samples, so seek of 1 means skip 32 bits */
    if (sf_seek(soundfile.fd, read_start, SEEK_SET)<0)
    {
        fprintf(stderr, "Error while seeking to sample %"PRId64"\n", start);
        exit(1);
    }

    long num_read = sf_read_short(soundfile.fd, buf_read_start, read_len * sf_info->channels);
    debug("read %li samples\n", num_read);

#if 0
    for (uint8_t *buf_read_start = (uint8_t*) buf; buf_read_start<(uint8_t*)buf+buf_size; buf_read_start++)
        printf("%s%02x",((void*)buf_read_start-(void*)buf)%40==0?"\n":" ",*buf_read_start);
    printf("\n");
#endif

    if (num_read != read_len * sf_info->channels)
    {
        fprintf(stderr, "Could read only %li of %"PRId64" samples (%"PRId64" available)\n",
                num_read, read_len, sf_info->frames);
        exit(1);
    }

    return sndbuf;
}
