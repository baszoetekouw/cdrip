
from pprint import pprint
import subprocess
import os
import pathlib
import fcntl

class CDPlayerException(Exception):
    pass


class CDPlayer:
    # from <linux/cdrom.h>
    CDROM_EJECT        = 0x5309
    CDROM_CLOSETRAY    = 0x5319
    CDROM_DRIVE_STATUS = 0x5326
    CDROM_LOCKDOOR     = 0x5329
    CDS_NO_INFO          = 0
    CDS_NO_DISC          = 1
    CDS_TRAY_OPEN        = 2
    CDS_DRIVE_NOT_REEADY = 3
    CDS_DISC_OK          = 4

    def __init__(self,device='/dev/cdrom'):
        if not pathlib.Path(device).resolve().is_block_device():
            raise CDPlayerException("`{}' is not a block device".format(device))
        if not self.is_cd():
            raise CDPlayerException("`{}' is not a CD player".format(device))
        self._device = device
        pass

    def open(self):
        return os.open(self.device(), os.O_RDONLY | os.O_NONBLOCK)

    def device(self):
        return self._device

    def status(self):
        with self.open() as cdrom:
            status = fcntl.ioctl(cdrom, self.CDROM_DRIVE_STATUS, 0)
        return status

    def is_cd(self):
        return self.status()!=self.CDS_NO_INFO

    def is_open(self):
        return self.status()==self.CDS_TRAY_OPEN

    def has_disc(self):
        return self.status()==self.CDS_DISC_OK

    def tray_open(self):
        with self.open() as cdrom:
            fcntl.ioctl(cdrom, self.CDROM_LOCKDOOR, 0)
            fcntl.ioctl(cdrom, self.CDROM_EJECT, 0)
        return

    def tray_close(self):
        with self.open() as cdrom:
            fcntl.ioctl(cdrom, self.CDROM_LOCKDOOR, 0)
            fcntl.ioctl(cdrom, self.CDROM_CLOSETRAY, 0)
        return

