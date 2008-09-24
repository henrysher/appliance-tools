#
# extends imgcreate fs.py : Filesystem related utilities and classes
# adds functionality in upstream fs.py for appliance-creator
#
# Copyright 2007, Red Hat  Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import os
import os.path
import sys
import errno
import stat
import subprocess
import random
import string
import logging

from imgcreate.fs import *
from imgcreate.errors import *


class Disk:
    def __init__(self, size, device = None):
        self._device = device
        self._size = size

    def create(self):
        pass

    def cleanup(self):
        pass

    def get_device(self):
        return self._device
    def set_device(self, path):
        self._device = path
    device = property(get_device, set_device)

    def get_size(self):
        return self._size
    size = property(get_size)

class RawDisk(Disk):
    def __init__(self, size, device):
        Disk.__init__(self, size, device)

    def fixed(self):
        return True

    def exists(self):
        return True

class LoopbackDisk(Disk):
    def __init__(self, lofile, size):
        Disk.__init__(self, size)
        self.lofile = lofile

    def fixed(self):
        return False

    def exists(self):
        return os.path.exists(self.lofile)

    def create(self):
        if self.device is not None:
            return

        losetupProc = subprocess.Popen(["/sbin/losetup", "-f"],
                                       stdout=subprocess.PIPE)
        losetupOutput = losetupProc.communicate()[0]

        if losetupProc.returncode:
            raise MountError("Failed to allocate loop device for '%s'" %
                             self.lofile)

        device = losetupOutput.split()[0]

        logging.debug("Losetup add %s mapping to %s"  % (device, self.lofile))
        rc = subprocess.call(["/sbin/losetup", device, self.lofile])
        if rc != 0:
            raise MountError("Failed to allocate loop device for '%s'" %
                             self.lofile)
        self.device = device

    def cleanup(self):
        if self.device is None:
            return
        logging.debug("Losetup remove %s" % self.device)
        rc = subprocess.call(["/sbin/losetup", "-d", self.device])
        self.device = None

class SparseLoopbackDisk(LoopbackDisk):
    def __init__(self, lofile, size):
        LoopbackDisk.__init__(self, lofile, size)

    def expand(self, create = False, size = None):
        flags = os.O_WRONLY
        if create:
            flags |= os.O_CREAT
            makedirs(os.path.dirname(self.lofile))

        if size is None:
            size = self.size

        logging.debug("Extending sparse file %s to %d" % (self.lofile, size))
        fd = os.open(self.lofile, flags)

        os.lseek(fd, size, 0)
        os.write(fd, '\x00')
        os.close(fd)

    def truncate(self, size = None):
        if size is None:
            size = self.size

        logging.debug("Truncating sparse file %s to %d" % (self.lofile, size))
        fd = os.open(self.lofile, os.O_WRONLY)
        os.ftruncate(fd, size)
        os.close(fd)

    def create(self):
        self.expand(create = True)
        LoopbackDisk.create(self)


class Mount:
    def __init__(self, mountdir):
        self.mountdir = mountdir

    def cleanup(self):
        self.unmount()

    def mount(self):
        pass

    def unmount(self):
        pass

class DiskMount(Mount):
    def __init__(self, disk, mountdir, fstype = None, rmmountdir = True):
        Mount.__init__(self, mountdir)

        self.disk = disk
        self.fstype = fstype
        self.rmmountdir = rmmountdir

        self.mounted = False
        self.rmdir   = False

    def cleanup(self):
        Mount.cleanup(self)
        self.disk.cleanup()

    def unmount(self):
        if self.mounted:
            logging.debug("Unmounting directory %s" % self.mountdir)
            rc = subprocess.call(["/bin/umount", self.mountdir])
            if rc == 0:
                self.mounted = False

        if self.rmdir and not self.mounted:
            try:
                os.rmdir(self.mountdir)
            except OSError, e:
                pass
            self.rmdir = False


    def __create(self):
        self.disk.create()


    def mount(self):
        if self.mounted:
            return

        if not os.path.isdir(self.mountdir):
            logging.debug("Creating mount point %s" % self.mountdir)
            os.makedirs(self.mountdir)
            self.rmdir = self.rmmountdir

        #self.__create()

        logging.debug("Mounting %s at %s" % (self.disk.device, self.mountdir))
        args = [ "/bin/mount", self.disk.device, self.mountdir ]
        if self.fstype:
            args.extend(["-t", self.fstype])

        rc = subprocess.call(args)
        if rc != 0:
            raise MountError("Failed to mount '%s' to '%s'" %
                             (self.disk.device, self.mountdir))

        self.mounted = True

class ExtDiskMount(DiskMount):
    def __init__(self, disk, mountdir, fstype, blocksize, fslabel, rmmountdir=True):
        DiskMount.__init__(self, disk, mountdir, fstype, rmmountdir)
        self.blocksize = blocksize
        self.fslabel = fslabel

    def __format_filesystem(self):
        logging.debug("Formating %s filesystem on %s" % (self.fstype, self.disk.device))
        rc = subprocess.call(["/sbin/mkfs." + self.fstype,
                              "-F", "-L", self.fslabel,
                              "-m", "1", "-b", str(self.blocksize),
                              self.disk.device])
        #                      str(self.disk.size / self.blocksize)])
        if rc != 0:
            raise MountError("Error creating %s filesystem" % (self.fstype,))
        logging.debug("Tuning filesystem on %s" % self.disk.device)
        subprocess.call(["/sbin/tune2fs", "-c0", "-i0", "-Odir_index",
                         "-ouser_xattr,acl", self.disk.device])

    def __resize_filesystem(self, size = None):
        current_size = os.stat(self.disk.lofile)[stat.ST_SIZE]

        if size is None:
            size = self.size

        if size == current_size:
            return

        if size > current_size:
            self.expand(size)

        self.__fsck()

        resize2fs(self.disk.lofile, size)
        return size

    def __create(self):
        resize = False
        if not self.disk.fixed() and self.disk.exists():
            resize = True

        self.disk.create()

        if resize:
            self.__resize_filesystem()
        else:
            self.__format_filesystem()

    def mount(self):
        self.__create()
        DiskMount.mount(self)

    def __fsck(self):
        logging.debug("Checking filesystem %s" % self.disk.lofile)
        subprocess.call(["/sbin/e2fsck", "-f", "-y", self.disk.lofile])

    def __get_size_from_filesystem(self):
        def parse_field(output, field):
            for line in output.split("\n"):
                if line.startswith(field + ":"):
                    return line[len(field) + 1:].strip()

            raise KeyError("Failed to find field '%s' in output" % field)

        dev_null = os.open("/dev/null", os.O_WRONLY)
        try:
            out = subprocess.Popen(['/sbin/dumpe2fs', '-h', self.disk.lofile],
                                   stdout = subprocess.PIPE,
                                   stderr = dev_null).communicate()[0]
        finally:
            os.close(dev_null)

        return int(parse_field(out, "Block count")) * self.blocksize

    def __resize_to_minimal(self):
        self.__fsck()

        #
        # Use a binary search to find the minimal size
        # we can resize the image to
        #
        bot = 0
        top = self.__get_size_from_filesystem()
        while top != (bot + 1):
            t = bot + ((top - bot) / 2)

            if not resize2fs(self.disk.lofile, t):
                top = t
            else:
                bot = t
        return top

    def resparse(self, size = None):
        self.cleanup()
        minsize = self.__resize_to_minimal()
        self.disk.truncate(minsize)
        return minsize


