#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <malloc.h>
#include <errno.h>
#include <sndfile.h>

#include "accuraterip.h"

int main(const int argc, const char *argv[])
{
	if (argc!=2)
	{
		fprintf(stderr,"Please specify filename\n");
		exit(1);
	}
	const char * filename = argv[1];
	SF_INFO info;
	memset(&info,0,sizeof(info));
	SNDFILE *fd = sf_open(filename, SFM_READ, &info);
	if (!fd)
	{
		fprintf(stderr,"Can't open file '%s': %s",filename,strerror(errno));
		exit(1);
	}
	printf("File opened succesfully.\n");
	printf("rate: %i, chan: %i, format: 0x%06x, sect: %i, seek: %i, frames: %li\n",
		info.samplerate, info.channels, info.format, info.sections, info.seekable, info.frames );

	if ( !(info.format & SF_FORMAT_PCM_16) || !(info.channels==2) )
	{
		fprintf(stderr, "This is not a stero PCM16 file\n");
		exit(1);
	}
	size_t num_samples = info.frames * info.channels;
	size_t buf_size = (num_samples) * sizeof(int16_t);
	int16_t * buf  = malloc(buf_size);
	memset(buf,0xff,buf_size);
	printf("buf size: %zu\n", buf_size);

	long num_read = sf_read_short(fd, buf, num_samples);
	fprintf(stdout, "read %li samples\n", num_read);

	//for (uint8_t *p = (uint8_t*) buf; p<(uint8_t*)buf+buf_size; p++) printf("%s%02x",((void*)p-(void*)buf)%40==0?"\n":" ",*p);
	//printf("\n");

	if (num_read!=info.frames*info.channels)
	{
		fprintf(stderr, "Could read only %li of %li frames\n", num_read, info.frames);
		exit(1);
	}

	sf_close(fd);

	/* now calc checksums */
	uint32_t crc_v1a = _accuraterip_checksum_v1(buf,buf_size,false,false);
	uint32_t crc_v2a = _accuraterip_checksum_v2(buf,buf_size,false,false);

	uint32_t crc_v1b = 0;
	uint32_t crc_v2b = 0;
	uint32_t crc_v1c = 0;
	uint32_t crc_v2c = 0;
	uint32_t crc_v1d = 0;
	uint32_t crc_v2d = 0;
	uint32_t crc_v1e = 0;
	uint32_t crc_v2e = 0;
	int result1 = accuraterip_checksum(&crc_v1b,&crc_v2b,buf,info.frames,info.channels,false,false);
	int result2 = accuraterip_checksum(&crc_v1c,&crc_v2c,buf,info.frames,info.channels,true,false);
	int result3 = accuraterip_checksum(&crc_v1d,&crc_v2d,buf,info.frames,info.channels,false,true);
	int result4 = accuraterip_checksum(&crc_v1e,&crc_v2e,buf,info.frames,info.channels,true,true);
	if (result1!=0||result2!=0||result3!=0||result4!=0)
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

	free(buf);

	return 0;
}
