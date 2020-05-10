/*
   Copyright (C) 2003-2005, 2007-2008, 2011-2012, 2014
   Rocky Bernstein <rocky@gnu.org>
   Copyright (C) 1996, 1997, 1998  Gerd Knorr <kraxel@bytesex.org>
   and Heiko Eißfeldt <heiko@hexco.de>

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.
   */
/*
   CD Info - prints various information about a CD, and detects the type of
   the CD.
   */
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>

#include <linux/version.h>
#include <linux/cdrom.h>

#include <cdio/cdio.h>
#include <cdio/bytesex.h>
#include <cdio/ds.h>
#include <cdio/util.h>
#include <cdio/cd_types.h>
#include <cdio/cdtext.h>
#include <cdio/mmc.h>
#include <cdio/audio.h>


#define err_exit(fmt, args...) \
{ fprintf(stderr, fmt, ##args); \
	myexit(p_cdio, EXIT_FAILURE); };

	void
myexit(CdIo_t *cdio, int rc)
{
	if (NULL != cdio) cdio_destroy(cdio);
	exit(rc);
}


/*! Device input routine. If successful we return an open CdIo_t
  pointer. On error the program exits.
  */
CdIo_t *
open_input(const char *psz_source)
{
	CdIo_t *p_cdio = cdio_open_am (psz_source, DRIVER_UNKNOWN, NULL);
	if (!p_cdio) {
		if (psz_source) {
			err_exit("Error in automatically selecting driver for input %s.\n",
					psz_source);
		} else {
			err_exit("%s", "Error in automatically selecting driver.\n");
		}
	}
	return p_cdio;
}

static void
print_cdtext_track_info(cdtext_t *p_cdtext, track_t i_track, const char *psz_msg) {

	if (NULL != p_cdtext) {
		cdtext_field_t i;

		printf("%s\n", psz_msg);

		for (i=0; i < MAX_CDTEXT_FIELDS; i++) {
			if (cdtext_get_const(p_cdtext, i, i_track)) {
				printf("\t%s: %s\n", cdtext_field2str(i), cdtext_get_const(p_cdtext, i, i_track));
			}
		}
	}
}

static void
print_cdtext_info(CdIo_t *p_cdio, track_t i_tracks, track_t i_first_track) {
	track_t i_last_track = i_first_track+i_tracks;
	cdtext_t *p_cdtext = cdio_get_cdtext(p_cdio);
	cdtext_lang_t *languages;
	cdtext_genre_t genre;

	int i, j;

	if(NULL == p_cdtext) {
		printf("No CD-TEXT on Disc.\n");
		return;
	}

	languages = cdtext_list_languages(p_cdtext);
	for(i=0; i<8; i++)
		if ( CDTEXT_LANGUAGE_UNKNOWN != languages[i]
				&& cdtext_select_language(p_cdtext, languages[i]))
		{
			printf("\nLanguage %d '%s':\n", i, cdtext_lang2str(languages[i]));

			print_cdtext_track_info(p_cdtext, 0, "CD-TEXT for Disc:");
			genre = cdtext_get_genre(p_cdtext);
			if ( CDTEXT_GENRE_UNUSED != genre)
				printf("\tGENRE_CODE: %d (%s)\n", genre, cdtext_genre2str(genre));

			for ( j = i_first_track ; j < i_last_track; j++ ) {
				char msg[50];
				sprintf(msg, "CD-TEXT for Track %2d:", j);
				print_cdtext_track_info(p_cdtext, j, msg);
			}
		}
}

	static void
print_analysis(int ms_offset, cdio_iso_analysis_t cdio_iso_analysis,
		cdio_fs_anal_t fs, int first_data, unsigned int num_audio,
		track_t i_tracks, track_t i_first_track,
		track_format_t track_format, CdIo_t *p_cdio)
{
	int need_lf;

	switch(CDIO_FSTYPE(fs)) {
		case CDIO_FS_AUDIO:
			if (num_audio > 0) {
				print_cdtext_info(p_cdio, i_tracks, i_first_track);
			}
			break;
		case CDIO_FS_ISO_9660:
			printf("CD-ROM with ISO 9660 filesystem");
			if (fs & CDIO_FS_ANAL_JOLIET) {
				printf(" and joliet extension level %d", cdio_iso_analysis.joliet_level);
			}
			if (fs & CDIO_FS_ANAL_ROCKRIDGE)
				printf(" and rockridge extensions");
			printf("\n");
			break;
		case CDIO_FS_ISO_9660_INTERACTIVE:
			printf("CD-ROM with CD-RTOS and ISO 9660 filesystem\n");
			break;
		case CDIO_FS_HIGH_SIERRA:
			printf("CD-ROM with High Sierra filesystem\n");
			break;
		case CDIO_FS_INTERACTIVE:
			printf("CD-Interactive%s\n", num_audio > 0 ? "/Ready" : "");
			break;
		case CDIO_FS_HFS:
			printf("CD-ROM with Macintosh HFS\n");
			break;
		case CDIO_FS_ISO_HFS:
			printf("CD-ROM with both Macintosh HFS and ISO 9660 filesystem\n");
			break;
		case CDIO_FS_UFS:
			printf("CD-ROM with Unix UFS\n");
			break;
		case CDIO_FS_EXT2:
			printf("CD-ROM with GNU/Linux EXT2 (native) filesystem\n");
			break;
		case CDIO_FS_3DO:
			printf("CD-ROM with Panasonic 3DO filesystem\n");
			break;
		case CDIO_FS_UDFX:
			printf("CD-ROM with UDFX filesystem\n");
			break;
		case CDIO_FS_UNKNOWN:
			printf("CD-ROM with unknown filesystem\n");
			break;
		case CDIO_FS_XISO:
			printf("CD-ROM with Microsoft X-BOX XISO filesystem\n");
			break;
	}

	need_lf = 0;
	if (first_data == 1 && num_audio > 0)
		need_lf += printf("mixed mode CD   ");
	if (fs & CDIO_FS_ANAL_XA)
		need_lf += printf("XA sectors   ");
	if (fs & CDIO_FS_ANAL_MULTISESSION)
		need_lf += printf("Multisession, offset = %i   ", ms_offset);
	if (fs & CDIO_FS_ANAL_HIDDEN_TRACK)
		need_lf += printf("Hidden Track   ");
	if (fs & CDIO_FS_ANAL_PHOTO_CD)
		need_lf += printf("%sPhoto CD   ",
				num_audio > 0 ? " Portfolio " : "");
	if (fs & CDIO_FS_ANAL_CDTV)
		need_lf += printf("Commodore CDTV   ");
	if (first_data > 1)
		need_lf += printf("CD-Plus/Extra   ");
	if (fs & CDIO_FS_ANAL_BOOTABLE)
		need_lf += printf("bootable CD   ");
	if (fs & CDIO_FS_ANAL_VIDEOCD && num_audio == 0) {
		need_lf += printf("Video CD   ");
	}
	if (fs & CDIO_FS_ANAL_SVCD)
		need_lf += printf("Super Video CD (SVCD) or Chaoji Video CD (CVD)");
	if (fs & CDIO_FS_ANAL_CVD)
		need_lf += printf("Chaoji Video CD (CVD)");
	if (need_lf) printf("\n");
}

/* ------------------------------------------------------------------------ */

	int
main(int argc, char *argv[])
{

	CdIo_t                *p_cdio=NULL;
	cdio_fs_anal_t         fs = CDIO_FS_AUDIO;
	int i;
	lsn_t                  start_track_lsn;      /* lsn of first track */
	lsn_t                  data_start     =  0;  /* start of data area */
	int                    ms_offset      =  0;
	track_t                i_tracks       =  0;
	track_t                i_first_track  =  0;
	unsigned int           num_audio      =  0;  /* # of audio tracks */
	unsigned int           num_data       =  0;  /* # of data tracks */
	int                    first_data     = -1;  /* # of first data track */
	int                    first_audio    = -1;  /* # of first audio track */
	bool                   b_playing_audio = false; /* currently playing a
													   CD-DA */
	cdio_iso_analysis_t    cdio_iso_analysis;
	char                  *media_catalog_number;
	char                  *isrc;
	discmode_t             discmode = CDIO_DISC_MODE_NO_INFO;
	cdio_drive_read_cap_t  i_read_cap = 0;
	cdio_drive_write_cap_t i_write_cap;
	cdio_drive_misc_cap_t  i_misc_cap;

	memset(&cdio_iso_analysis, 0, sizeof(cdio_iso_analysis));

	if (argc<2 || !argv[1]) {
		err_exit("please specify cdrom device");
	}
	const char * source_name = argv[1];
	p_cdio = open_input(source_name);

	if (p_cdio==NULL) {
		if (source_name) {
			err_exit("Error in opening device driver for input %s.\n", source_name);
		} else {
			err_exit("Error in opening device driver for unspecified input.\n")
		}
	}

	if (source_name==NULL) {
		source_name=strdup(cdio_get_arg(p_cdio, "source"));
		if (NULL == source_name) {
			err_exit("No input device given/found\n");
		}
	}

	printf("CD location   : %s\n",   source_name);
	printf("CD driver name: %s\n",   cdio_get_driver_name(p_cdio));
	printf("   access mode: %s\n\n", cdio_get_arg(p_cdio, "access-mode"));

	discmode = cdio_get_discmode(p_cdio);
	printf("Disc mode is listed as: %s\n", discmode2str[discmode]);

	i_first_track = cdio_get_first_track_num(p_cdio);

	if (CDIO_INVALID_TRACK == i_first_track) {
		err_exit("Can't get first track number. I give up%s.\n", "");
	}

	i_tracks = cdio_get_num_tracks(p_cdio);

	if (CDIO_INVALID_TRACK == i_tracks) {
		err_exit("Can't get number of tracks. I give up.%s\n", "");
	}

	printf("CD-ROM Track List (%i - %i)\n", i_first_track, i_tracks);

	printf("  #: MSF       LSN    Type   Green? Copy?");
	if ( CDIO_DISC_MODE_CD_DA == discmode
			|| CDIO_DISC_MODE_CD_MIXED == discmode )
		printf(" Channels Premphasis?");
	printf("\n");

	start_track_lsn = cdio_get_track_lsn(p_cdio, i_first_track);

	/* Read and possibly print track information. */
	for (i = i_first_track; i <= CDIO_CDROM_LEADOUT_TRACK; i++) {
		msf_t msf;
		char *psz_msf;
		track_format_t track_format;

		if (!cdio_get_track_msf(p_cdio, i, &msf)) {
			err_exit("cdio_track_msf for track %i failed, I give up.\n", i);
		}

		track_format = cdio_get_track_format(p_cdio, i);
		psz_msf = cdio_msf_to_str(&msf);
		if (i == CDIO_CDROM_LEADOUT_TRACK) {
			lsn_t lsn= cdio_msf_to_lsn(&msf);
			long unsigned int i_bytes_raw = lsn * CDIO_CD_FRAMESIZE_RAW;
			long unsigned int i_bytes_formatted = lsn - start_track_lsn;

			printf( "%3d: %8s  %06lu leadout ", (int) i, psz_msf,
					(long unsigned int) lsn );

			switch (discmode) {
				case CDIO_DISC_MODE_DVD_ROM:
				case CDIO_DISC_MODE_DVD_RAM:
				case CDIO_DISC_MODE_DVD_R:
				case CDIO_DISC_MODE_DVD_RW:
				case CDIO_DISC_MODE_DVD_PR:
				case CDIO_DISC_MODE_DVD_PRW:
				case CDIO_DISC_MODE_DVD_OTHER:
				case CDIO_DISC_MODE_CD_DATA:
					i_bytes_formatted *= CDIO_CD_FRAMESIZE;
					break;
				case CDIO_DISC_MODE_CD_DA:
					i_bytes_formatted *= CDIO_CD_FRAMESIZE_RAW;
					break;
				case CDIO_DISC_MODE_CD_XA:
				case CDIO_DISC_MODE_CD_MIXED:
					i_bytes_formatted *= CDIO_CD_FRAMESIZE_RAW0;
					break;
				default:
					i_bytes_formatted *= CDIO_CD_FRAMESIZE_RAW;
			}

			if (i_bytes_raw < 1024)
				printf( "(%lu bytes", i_bytes_raw );
			if (i_bytes_raw < 1024 * 1024)
				printf( "(%lu KB", i_bytes_raw / 1024 );
			else
				printf( "(%lu MB", i_bytes_raw / (1024 * 1024) );

			printf(" raw, ");
			if (i_bytes_formatted < 1024)
				printf( "%lu bytes", i_bytes_formatted );
			if (i_bytes_formatted < 1024 * 1024)
				printf( "%lu KB", i_bytes_formatted / 1024 );
			else
				printf( "%lu MB", i_bytes_formatted / (1024 * 1024) );

			printf(" formatted)\n");

			free(psz_msf);
			break;
		} else {
			const char *psz;
			printf( "%3d: %8s  %06lu %-6s %-5s  ", (int) i, psz_msf,
					(long unsigned int) cdio_msf_to_lsn(&msf),
					track_format2str[track_format],
					cdio_get_track_green(p_cdio, i)? "true " : "false");

			switch (cdio_get_track_copy_permit(p_cdio, i)) {
				case CDIO_TRACK_FLAG_FALSE:
					psz="no";
					break;
				case CDIO_TRACK_FLAG_TRUE:
					psz="yes";
					break;
				case CDIO_TRACK_FLAG_UNKNOWN:
					psz="?";
					break;
				case CDIO_TRACK_FLAG_ERROR:
				default:
					psz="error";
					break;
			}
			printf("%-5s", psz);

			if (TRACK_FORMAT_AUDIO == track_format) {
				const int i_channels = cdio_get_track_channels(p_cdio, i);
				switch (cdio_get_track_preemphasis(p_cdio, i)) {
					case CDIO_TRACK_FLAG_FALSE:
						psz="no";
						break;
					case CDIO_TRACK_FLAG_TRUE:
						psz="yes";
						break;
					case CDIO_TRACK_FLAG_UNKNOWN:
						psz="?";
						break;
					case CDIO_TRACK_FLAG_ERROR:
					default:
						psz="error";
						break;
				}
				if (i_channels == -2)
					printf(" %-8s", "unknown");
				else if (i_channels == -1)
					printf(" %-8s", "error");
				else
					printf(" %-8d", i_channels);
				printf( " %s", psz);
			}

			printf( "\n" );

		}
		free(psz_msf);

		if (TRACK_FORMAT_AUDIO == track_format) {
			num_audio++;
			if (-1 == first_audio) first_audio = i;
		} else {
			num_data++;
			if (-1 == first_data)  first_data = i;
		}
		/* skip to leadout? */
		if (i == i_tracks) i = CDIO_CDROM_LEADOUT_TRACK-1;
	}

	if (cdio_is_discmode_cdrom(discmode)) {
		/* get and print MCN */
		printf("Media Catalog Number (MCN): ");

		media_catalog_number = cdio_get_mcn(p_cdio);

		if (NULL == media_catalog_number) {
			if (i_read_cap & CDIO_DRIVE_CAP_READ_MCN)
				printf("not available\n");
			else
				printf("not supported by drive/driver\n");
		} else {
			printf("%s\n", media_catalog_number);
			cdio_free(media_catalog_number);
		}

		/* get and print track ISRCs */

		{
			for (i = first_audio; i < first_audio + num_audio; i++) {
				isrc = cdio_get_track_isrc(p_cdio, i);

				if (NULL != isrc) {
					printf("TRACK %2d ISRC: %s\n", i, isrc);
					cdio_free(isrc);
				}
			}
		}

		/* List number of sessions */
		{
			lsn_t i_last_session;
			printf("Last CD Session LSN: ");
			if (DRIVER_OP_SUCCESS == cdio_get_last_session(p_cdio, &i_last_session))
			{
				printf("%d\n", i_last_session);
			} else {
				if (i_misc_cap & CDIO_DRIVE_CAP_MISC_MULTI_SESSION)
					printf("failed\n");
				else
					printf("not supported by drive/driver\n");
			}
		}
	}

	{
		printf("CD Analysis Report\n");

		/* try to find out what sort of CD we have */
		if (num_audio > 0) {
			/* may be a "real" audio CD or hidden track CD */

			msf_t msf;
			cdio_get_track_msf(p_cdio, i_first_track, &msf);

			/* CD-I/Ready says start_track_lsn <= 30*75 then CDDA */
			if (start_track_lsn > 100 /* 100 is just a guess */) {
				fs = cdio_guess_cd_type(p_cdio, 0, 1, &cdio_iso_analysis);
				if ((CDIO_FSTYPE(fs)) != CDIO_FS_UNKNOWN)
					fs |= CDIO_FS_ANAL_HIDDEN_TRACK;
				else {
					fs &= ~CDIO_FS_MASK; /* del filesystem info */
					printf("Oops: %lu unused sectors at start, "
							"but hidden track check failed.\n",
							(long unsigned int) start_track_lsn);
				}
			}
			print_analysis(ms_offset, cdio_iso_analysis, fs, first_data, num_audio,
					i_tracks, i_first_track,
					cdio_get_track_format(p_cdio, 1), p_cdio);
		}
		if (num_data > 0) {
			/* we have data track(s) */
			int j;

			for (j = 2, i = first_data; i <= i_tracks; i++) {
				msf_t msf;
				track_format_t track_format = cdio_get_track_format(p_cdio, i);

				cdio_get_track_msf(p_cdio, i, &msf);

				switch ( track_format ) {
					case TRACK_FORMAT_AUDIO:
					case TRACK_FORMAT_ERROR:
						break;
					case TRACK_FORMAT_CDI:
					case TRACK_FORMAT_XA:
					case TRACK_FORMAT_DATA:
					case TRACK_FORMAT_PSX:
						;
				}

				start_track_lsn = (i == 1) ? 0 : cdio_msf_to_lsn(&msf);

				/* save the start of the data area */
				if (i == first_data)
					data_start = start_track_lsn;

				/* skip tracks which belong to the current walked session */
				if (start_track_lsn < data_start + cdio_iso_analysis.isofs_size)
					continue;

				fs = cdio_guess_cd_type(p_cdio, start_track_lsn, i,
						&cdio_iso_analysis);

				if (i > 1) {
					/* track is beyond last session -> new session found */
					ms_offset = start_track_lsn;
					printf( "session #%d starts at track %2i, LSN: %lu,"
							" ISO 9660 blocks: %6i\n",
							j++, i, (unsigned long int) start_track_lsn,
							cdio_iso_analysis.isofs_size);
					printf( "ISO 9660: %i blocks, label `%.32s'\n",
							cdio_iso_analysis.isofs_size, cdio_iso_analysis.iso_label);
					fs |= CDIO_FS_ANAL_MULTISESSION;
				} else {
					print_analysis(ms_offset, cdio_iso_analysis, fs, first_data,
							num_audio, i_tracks, i_first_track,
							track_format, p_cdio);
				}

				if ( !(CDIO_FSTYPE(fs) == CDIO_FS_ISO_9660 ||
							CDIO_FSTYPE(fs) == CDIO_FS_ISO_HFS  ||
							/* CDIO_FSTYPE(fs) == CDIO_FS_ISO_9660_INTERACTIVE)
							   && (fs & XA))) */
					CDIO_FSTYPE(fs) == CDIO_FS_ISO_9660_INTERACTIVE) )
						/* no method for non-ISO9660 multisessions */
						break;
			}
		}
	}

	myexit(p_cdio, EXIT_SUCCESS);
	/* Not reached:*/
	return(EXIT_SUCCESS);
}
