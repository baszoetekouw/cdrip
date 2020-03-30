#include "accuraterip.h"

#include <stdlib.h>
#include <stdio.h>
#include <getopt.h>
#include <string.h>
#include <inttypes.h>
#include <assert.h>

#define N 255

bool VERBOSE = false;

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
#if OBSOLETE_IMPLEMENTATIONS
	printf("  --test (-t)    : show lots of test output (different variations of checksums)\n");
#endif
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

opts_t parse_args(const int argc, char ** argv)
{
	opts_t opts = { NULL, 0, -1, false, false, false };

	const char * const  short_options  = "hflvt";
	const struct option long_options[] =
	{
		{"help",    no_argument, NULL, 'h'},
		{"verbose", no_argument, NULL, 'v'},
#if OBSOLETE_IMPLEMENTATIONS
		{"test",    no_argument, NULL, 't'},
#endif
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
#if OBSOLETE_IMPLEMENTATIONS
			case 't':
				opts.test = true;
				break;
#endif
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
