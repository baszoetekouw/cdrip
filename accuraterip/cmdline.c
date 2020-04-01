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
	printf("Syntax: accuraterip [-v] [-f] [-l] <filename.wav> [<start1>[,<length1>] [<start2>[,<length2>] ...]] \n");
	printf("\n");
	printf("Available options:\n");
	printf("  --first (-f)   : track is first on disc (first 5 frames are ignored)\n");
	printf("  --last (-l)    : track is last on disc (final 5 frames are ignored)\n");
#if OBSOLETE_IMPLEMENTATIONS
	printf("  --test (-t)    : show lots of test output (different variations of checksums)\n");
#endif
	printf("  --verbose (-v) : show verbose output\n");
	printf("\n");
	printf("<startN>  :  start time of Nth track in file (default: start of file)\n");
	printf("<lengthN> :  length of Nth track in file (default: from <start> until the end of the file\n");
	printf("\n");
	printf("Start and length times can be specififed as:\n");
	printf("  Ns for N samples, or\n");
    printf("  N  for N seconds, or\n");
    printf("  [m:]s:f for minutes, seconds and frames\n");
	printf("  (1 frame  is 1/75 seconds, or 588 samples)\n");

	if (error==NULL)
		exit(0);
	else
		exit(1);
}

opts_t parse_args(const int argc, char ** argv) {
    opts_t opts = {NULL, false, 1, {{0, -1, false, false}}};

    const char *const short_options = "hflvt";
    const struct option long_options[] =
            {
                    {"help", no_argument, NULL, 'h'},
                    {"verbose", no_argument, NULL, 'v'},
#if OBSOLETE_IMPLEMENTATIONS
                    {"test",    no_argument, NULL, 't'},
#endif
                    {"first", no_argument, NULL, 'f'},
                    {"last", no_argument, NULL, 'l'},
                    {NULL, 0, NULL, 0},
            };

    while (1) {
        int opt_idx;
        char buff[N];
        int c = getopt_long(argc, argv, short_options, long_options, &opt_idx);
        opterr = 0; /* don't print error messages */

        if (c == -1)
            break;

        switch (c) {
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
            /* note: specifying -f/-l and multiple tracks doesn't make sens;
             * this is handled below, after parsing all arguments */
            case 'f':
                opts.tracks[0].is_first_track = true;
                break;
            case 'l':
                opts.tracks[0].is_last_track = true;
                break;
            default:
                help("Unknown option specified");
        }
    }
    int args_left = argc - optind;

    if (args_left < 1) help("Too few arguments");

    opts.filename = argv[optind];

    if (args_left>1)
    {
        opts.num_tracks = 0;
        /* process optional track spec (<start>,<length>) */
        for (unsigned int i = optind + 1; i < argc; i++) {
            /* we found a new track */
            opts.num_tracks++;
            track_t *const track = &opts.tracks[opts.num_tracks - 1];

            char buff[N];
            strncpy(buff, argv[i], N);
            /* should be <start>,<length> so find position of comma */
            char *len_part = strchr(buff, ',');
            if (len_part != NULL) {
                /* comma is present, so set comma to \0 to terminate first part of the string and increase pos by 1 */
                *len_part = '\0';
                len_part++;
            }

            /* parse first part of the argument */
            track->sample_start = parse_time(buff, N);
            /* optionally parse second part (length) */
            if (len_part != NULL && *len_part != '\0') {
                track->sample_length = parse_time(len_part, N - (len_part - buff));
            }
        }
    }
    /* correctly set first and last track, but only if we specified at least two tracks */
    if (opts.num_tracks>1)
    {
        /* check if the user specified -l or -f, which doesn't make sense if
         * he also specified more than one track */
        if (opts.tracks[0].is_first_track || opts.tracks[0].is_last_track)
        {
            help("Specifying both -f/-l and multiple tracks doesn't make sense");
        }
        opts.tracks[0].is_first_track = true;
        opts.tracks[opts.num_tracks-1].is_last_track = true;
    }


	debug("Input filename: '%s'\n", opts.filename);
    debug("Number of tracks: %d\n", opts.num_tracks);
    for (int i=0; i<opts.num_tracks; i++)
    {
        const track_t * const track = &opts.tracks[i];
        char buff1[N], buff2[N];
        debug("  - track %d: start %s (%"PRId64"), len %s (%"PRId64") (%c/%c)\n", i,
                samplestostr(buff1, N, track->sample_start ), track->sample_start,
                samplestostr(buff2, N, track->sample_length), track->sample_length,
                track->is_first_track ? 'f' : '-',
                track->is_last_track  ? 'l' : '-' );
    }

	return opts;
}
