#pragma clang diagnostic push
#pragma ide diagnostic ignored "OCUnusedMacroInspection"
/* for strtol */
#define _ISOC99_SOURCE

#include <stdlib.h>
#include <stdio.h>
#include <getopt.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>
#include <sndfile.h>

#include "accuraterip.h"

typedef struct {
	const char * filename;
	int64_t sample_start;
	int64_t sample_length;
	bool is_first_track;
	bool is_last_track;
	bool test;
} opts_t;

#define N 255

static bool VERBOSE = false;
#define debug(a...) ({ if (VERBOSE) printf(a); })

int help(const char * const error)
{
	if (error!=NULL)
	{
		printf("ERROR: %s\n\n", error);
	}
	printf("Syntax: accuraterip [-v] [-f] [-l] <filename.wav> [<start> [<length>]]\n");
	printf("\n");
	printf("Available options:\n");
	printf("  --first (-f)   : track is first on disc (first 5 frames are ignored)\n");
	printf("  --last (-l)    : track is last on disc (final 5 frames are ignored)\n");
	printf("  --test (-t)    : show lots of test output (different variations of checksums)\n");
	printf("  --verbose (-v) : show verbose output\n");
	printf("\n");
	printf("<start>  :  start time of track in file (default: start of file)\n");
	printf("<length> :  length of track in file (default: from <start> until the end of the file\n");
	printf("\n");
	printf("Start and length times can be specififed as:\n");
	printf("  Ns for N samples, or\n");
	printf("  [[m:]s:]f for minutes, seconds and frames\n");
	printf("  (1 frame  is 1/75 seconds, or 588 samples)\n");

	if (error==NULL)
		exit(0);
	else
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


opts_t parse_args(const int argc, char ** argv)
{
	opts_t opts = { NULL, 0, -1, false, false, false };

	const char * const  short_options  = "hflvt";
	const struct option long_options[] =
	{
		{"help",    no_argument, NULL, 'h'},
		{"verbose", no_argument, NULL, 'v'},
		{"test",    no_argument, NULL, 't'},
		{"first",   no_argument, NULL, 'f'},
		{"last",    no_argument, NULL, 'l'},
		{NULL,      0,           NULL, 0  },
	};

	while (1)
	{
		int opt_idx;
		char buff[N];
		int c = getopt_long(argc, argv, short_options, long_options, &opt_idx);
		opterr = 0; /* don't print error messages */

		if (c==-1)
			break;

		switch (c)
		{
			case 'h':
				help(NULL);
				assert(0); /* never reached */
			case '?':
				snprintf(buff, N, "Invalid option '-%c'", optopt);
				help(buff);
				assert(0); /* never reached */
			case 'v':
				VERBOSE = true;
				break;
			case 't':
				opts.test = true;
				break;
			case 'f':
				opts.is_first_track = true;
				break;
			case 'l':
				opts.is_last_track = true;
				break;
		    default:
		        help("Unknown option specified");
		}
	}
	int args_left = argc - optind;

	if (args_left<1) help("Too few arguments");
	if (args_left>3) help("Too many arguments");

	opts.filename = argv[optind];

	if (args_left>=2)
	{
		char buff[N];
		strncpy(buff, argv[optind+1], N);
		opts.sample_start = parse_time(buff, N);
	}

	if (args_left>2)
	{
		char buff[N];
		strncpy(buff, argv[optind+2], N);
		opts.sample_length = parse_time(buff, N);
	}

	debug("input filename: '%s'\n", opts.filename);
	debug("Track type: %sfirst,%slast\n", opts.is_first_track ? "" : "not ", opts.is_last_track ? "" : "not ");
	debug("start sample: '%"PRId64"'\n", opts.sample_start);
	debug("number of samples: '%"PRId64"'\n", opts.sample_length);

	return opts;
}

int main(const int argc, char **argv)
{
	opts_t options = parse_args(argc,argv);

	debug("Source file: '%s'\n", options.filename);
	debug("Start at sample #: %"PRId64"\n", options.sample_start);
	debug("Read samples: %"PRId64"\n", options.sample_length);

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
	if (sf_seek(fd,options.sample_start,SEEK_SET)<0)
	{
		fprintf(stderr, "Error while seeking to sample %"PRId64"\n", options.sample_start);
		exit(1);
	}

	/* Note: 1 sample consists of 2 16-bit values (left and right channel) */
	int64_t num_samples;
	if (options.sample_length>0)
		num_samples = options.sample_length;
	else
		num_samples = info.frames-options.sample_start;

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
	{
		uint32_t crc_v1 = 0;
		uint32_t crc_v2 = 0;
		int result = accuraterip_checksum(&crc_v1, &crc_v2, buf, num_samples, info.channels,
		                                  options.is_first_track, options.is_last_track);
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

