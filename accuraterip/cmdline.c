/* for strtol */
#define _ISOC99_SOURCE

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sndfile.h>

#include "accuraterip.h"

typedef struct {
	const char * filename;
	size_t sample_start;
	size_t sample_length;
} opts_t;

#define N 255


int help(const char * const error)
{
	if (error!=NULL)
	{
		printf("ERROR: %s\n\n", error);
	}
	printf("Syntax: accuraterip <filename.wav> [ start [ length ] ]\n");
	printf("  start and length can be specified as:\n");
	printf("  Ns for N samples, or\n");
	printf("  m:s:f for minutes, seconds and frames\n");
	printf("  (1 frame  is 1/75 seconds, or 588 samples)\n");
	exit(1);
}

size_t parse_time(const char * const time_str, const size_t buff_size)
{
	/* We're going to parse a time input string
	 * These strings can be either in the form "<samples>s" to specifiy a fixed number of samples
	 * right away, or in the form "[[<min>:]<sec>:]<frames>" to specify minutes, seconds, and frames.
	 * Note: 4 bytes (16 bits x 2 channels) in a sample, 588 samples in a frame, 75 frames in a second
	 */

	/* copy the string to a local buffer, to make sure it's NULL-terminated */
	char buff[buff_size+1];
	memcpy(buff,time_str,buff_size);
	buff[buff_size] = '\0';

	/* pointer to current position in buffer */
	char *p1, *p2, *p3;

	/* fetch first number in the string */
	long num1 = strtol(buff,&p1,10);
	if (num1<0)
	{
		/* invalid (negative) number was specified */
		help("Invalid time specification (negative number)");
	}
	if (p1==buff)
	{
		/* pointer hasn't moved, so there was no number to decode */
		help("Invalid time specified");
	}

	/* if the next char is an 's' (or 'S'), assume first number is a number of samples */
	if (*p1=='s' || *p1=='S')
	{
		return num1;
	}

	/* fetch second number in the string */
	long num2 = strtol(++p1,&p2,10);
	if (num2<0)
	{
		/* invalid (negative) number was specified */
		help("Invalid time specification (negative number)");
	}
	if (p2==p1)
	{
		/* pointer hasn't moved, so there was no number to decode,
		 * which means num1 is the final answer, and should be interpretated as a number of frames */
		return num1*SAMPLES_PER_FRAME;
	}

	/* fetch third number in the string */
	long num3 = strtol(++p2,&p3,10);
	if (num3<0)
	{
		/* invalid (negative) number was specified */
		help("Invalid time specification (negative number)");
	}
	if (p3==p2)
	{
		/* pointer hasn't moved, so there was no number to decode,
		 * which means num1:num2 is the final answer, and should be interpretated as seconds:frames */
		return num1*SAMPLES_PER_SECOND + num2*SAMPLES_PER_FRAME;
	}

	/* otherwise, we got minutes:seconds:frames */
	return num1*SAMPLES_PER_MINUTE + num2*SAMPLES_PER_SECOND + num3*SAMPLES_PER_FRAME;
}

opts_t parse_args(const int argc, const char * argv[])
{
	opts_t opts = { NULL, -1, -1 };

	if (argc<2) help("Too few arguments");
	if (argc>4) help("Too many arguments");

	opts.filename = argv[1];

	printf("input filename: '%s'\n",opts.filename);

	if (argc>2)
	{
		char buff[N];
		strncpy(buff,argv[2],N-1);
		opts.sample_start = parse_time(buff,N);
		printf("start sample: '%zu'\n",opts.sample_start);
	}

	if (argc>3)
	{
		char buff[N];
		strncpy(buff,argv[2],N-1);
		opts.sample_length = parse_time(argv[3],N);
		printf("length sample: '%zu'\n",opts.sample_length);
	}

	return opts;
}

int main(const int argc, const char *argv[])
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
