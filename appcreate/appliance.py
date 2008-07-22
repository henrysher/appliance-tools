#
# appliance.py: ApplianceImageCreator class
#
# Copyright 2007-2008, Red Hat  Inc.
# Copyright 2008, Daniel P. Berrange
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
import glob
import shutil
import subprocess
import logging

from imgcreate.errors import *
from imgcreate.fs import *
from imgcreate.creator import *

import stat

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

class PartitionedMount:
    def __init__(self, disks, mountdir):
        self.mountdir = mountdir
        self.disks = {}
        for name in disks.keys():
            self.disks[name] = { 'disk': disks[name],  # Disk object
                                 'mapped': False, # True if kpartx mapping exists
                                 'numpart': 0, # Number of allocate partitions
                                 'partitions': [], # indexes to self.partitions
                                 'extended': 0, # Size of extended partition
                                 'offset': 0 } # Offset of next partition

        self.partitions = []
        self.mapped = False
        self.mountOrder = []
        self.unmountOrder = []

    def add_partition(self, size, disk, mountpoint, fstype = None):
        self.partitions.append({'size': size,
                                'mountpoint': mountpoint, # Mount relative to chroot
                                'fstype': fstype,
                                'disk': disk,  # physical disk name holding partition
                                'device': None, # kpartx device node for partition
                                'mount': None, # Mount object
                                'num': None}) # Partition number

    def __format_disks(self):
        logging.debug("Formatting disks")
        for dev in self.disks.keys():
            d = self.disks[dev]
            logging.debug("Initializing partition table for %s" % (d['disk'].device))
            rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mklabel", "msdos"])
            if rc != 0:
                raise MountError("Error writing partition table on %s" % d.device)

        logging.debug("Assigning partitions to disks")
        for n in range(len(self.partitions)):
            p = self.partitions[n]

            if not self.disks.has_key(p['disk']):
                raise MountError("No disk %s for partition %s" % (p['disk'], p['mountpoint']))

            d = self.disks[p['disk']]
            d['numpart'] += 1
            if d['numpart'] > 3:
                # Increase allocation of extended partition to hold this partition
                d['extended'] += p['size']
                p['type'] = 'logical'
                p['num'] = d['numpart'] + 1
            else:
                p['type'] = 'primary'
                p['num'] = d['numpart']

            p['start'] = d['offset']
            d['offset'] += p['size']
            d['partitions'].append(n)
            logging.debug("Assigned %s to %s%d at %d at size %d" % (p['mountpoint'], p['disk'], p['num'], p['start'], p['size']))

        # XXX we should probably work in cylinder units to keep fdisk happier..
        start = 0
        logging.debug("Creating partitions")
        for p in self.partitions:
            d = self.disks[p['disk']]
            if p['num'] == 5:
                logging.debug("Added extended part at %d of size %d" % (p['start'], d['extended']))
                rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mkpart", "extended",
                                      "%dM" % p['start'], "%dM" % (p['start'] + d['extended'])])

            logging.debug("Add %s part at %d of size %d" % (p['type'], p['start'], p['size']))
            rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mkpart",
                                  p['type'], "%dM" % p['start'], "%dM" % (p['start']+p['size'])])

            # XXX disabled return code check because parted always fails to
            # reload part table with loop devices. Annoying because we can't
            # distinguish this failure from real partition failures  :-( 
            if rc != 0 and 1 == 0:
                raise MountError("Error creating partition on %s" % d['disk'].device)

    def __map_partitions(self):
        for dev in self.disks.keys():
            d = self.disks[dev]
            if d['mapped']:
                continue

            kpartx = subprocess.Popen(["/sbin/kpartx", "-l", d['disk'].device],
                                      stdout=subprocess.PIPE)

            kpartxOutput = kpartx.communicate()[0].split("\n")
            # Strip trailing blank
            kpartxOutput = kpartxOutput[0:len(kpartxOutput)-1]

            if kpartx.returncode:
                raise MountError("Failed to query partition mapping for '%s'" %
                                 d.device)

            # Quick sanity check that the number of partitions matches
            # our expectation. If it doesn't, someone broke the code
            # further up
            if len(kpartxOutput) != d['numpart']:
                raise MountError("Unexpected number of partitions from kpartx: %d != %d" %
                                 (len(kpartxOutput), d['numpart']))

            for i in range(len(kpartxOutput)):
                line = kpartxOutput[i]
                newdev = line.split()[0]
                mapperdev = "/dev/mapper/" + newdev
                loopdev = d['disk'].device + newdev[-1]

                logging.debug("Dev %s: %s -> %s" % (newdev, loopdev, mapperdev))
                pnum = d['partitions'][i]
                self.partitions[pnum]['device'] = loopdev

                # grub's install wants partitions to be named
                # to match their parent device + partition num
                # kpartx doesn't work like this, so we add compat
                # symlinks to point to /dev/mapper
                os.symlink(mapperdev, loopdev)

            logging.debug("Adding partx mapping for %s" % d['disk'].device)
            rc = subprocess.call(["/sbin/kpartx", "-a", d['disk'].device])
            if rc != 0:
                raise MountError("Failed to map partitions for '%s'" %
                                 d['disk'].device)
            d['mapped'] = True


    def __unmap_partitions(self):
        for dev in self.disks.keys():
            d = self.disks[dev]
            if not d['mapped']:
                continue

            logging.debug("Removing compat symlinks")
            for pnum in d['partitions']:
                if self.partitions[pnum]['device'] != None:
                    os.unlink(self.partitions[pnum]['device'])
                    self.partitions[pnum]['device'] = None

            logging.debug("Unmapping %s" % d['disk'].device)
            rc = subprocess.call(["/sbin/kpartx", "-d", d['disk'].device])
            if rc != 0:
                raise MountError("Failed to unmap partitions for '%s'" %
                                 d['disk'].device)

            d['mapped'] = False


    def __calculate_mountorder(self):
        for p in self.partitions:
            self.mountOrder.append(p['mountpoint'])
            self.unmountOrder.append(p['mountpoint'])

        self.mountOrder.sort()
        self.unmountOrder.sort()
        self.unmountOrder.reverse()
        print str(self.mountOrder)

    def cleanup(self):
        self.unmount()
        self.__unmap_partitions()
        for dev in self.disks.keys():
            d = self.disks[dev]
            try:
                d['disk'].cleanup()
            except:
                pass

    def unmount(self):
        for mp in self.unmountOrder:
            if mp == 'swap':
                continue
            p = None
            for p1 in self.partitions:
                if p1['mountpoint'] == mp:
                    p = p1
                    break

            if p['mount'] != None:
                try:
                    p['mount'].cleanup()
                except:
                    pass
                p['mount'] = None

    def mount(self):
        for dev in self.disks.keys():
            d = self.disks[dev]
            d['disk'].create()

        self.__format_disks()
        self.__map_partitions()
        self.__calculate_mountorder()

        for mp in self.mountOrder:
            p = None
            for p1 in self.partitions:
                if p1['mountpoint'] == mp:
                    p = p1
                    break

            if mp == 'swap':
                subprocess.call(["/sbin/mkswap", p['device']])
                continue

            rmmountdir = False
            if p['mountpoint'] == "/":
                rmmountdir = True
            pdisk = ExtDiskMount(RawDisk(p['size'] * 1024 * 1024, p['device']),
                                 self.mountdir + p['mountpoint'],
                                 p['fstype'],
                                 4096,
                                 p['mountpoint'],
                                 rmmountdir)
            pdisk.mount()
            p['mount'] = pdisk

    def resparse(self, size = None):
        # Can't re-sparse a disk image - too hard
        pass


class ApplianceImageCreator(ImageCreator):
    """Installs a system into a file containing a partitioned disk image.

    ApplianceImageCreator is an advanced ImageCreator subclass; a sparse file
    is formatted with a partition table, each partition loopback mounted
    and the system installed into an virtual disk. The disk image can
    subsequently be booted in a virtual machine or accessed with kpartx

    """

    def __init__(self, ks, name, format="raw"):
        """Initialize a ApplianceImageCreator instance.

        This method takes the same arguments as ImageCreator.__init__()

        """
        ImageCreator.__init__(self, ks, name)

        self.__instloop = None
        self.__imgdir = None
        self.__format = format
        self.__disks = {}
        self.__vmem = 512
        self.__vcpu = 1
        

    def _get_fstab(self):
        s = ""
        for mp in self.__instloop.mountOrder:
            p = None
            for p1 in self.__instloop.partitions:
                if p1['mountpoint'] == mp:
                    p = p1
                    break

            s +=  "%(device)s  %(mountpoint)s %(fstype)s    defaults,noatime 0 0\n" %  {
                'device': "/dev/%s%-d" % (p['disk'], p['num']),
                'mountpoint': p['mountpoint'],
                'fstype': p['fstype'] }

        s += "devpts     /dev/pts  devpts  gid=5,mode=620   0 0\n"
        s += "tmpfs      /dev/shm  tmpfs   defaults         0 0\n"
        s += "proc       /proc     proc    defaults         0 0\n"
        s += "sysfs      /sys      sysfs   defaults         0 0\n"
        return s
    
    
    def _create_mkinitrd_config(self):
        #write  to tell which modules to be included in initrd
        
        mkinitrd = ""
        mkinitrd += "PROBE=\"no\"\n"
        mkinitrd += "MODULES=\"ext3 ata_piix sd_mod libata scsi_mod\"\n"
        mkinitrd += "rootfs=\"ext3\"\n"
        mkinitrd += "rootopts=\"defaults\"\n"
        
        logging.debug("Writing mkinitrd config %s/etc/sysconfig/mkinitrd" % self._instroot)
        os.makedirs(self._instroot + "/etc/sysconfig/",mode=644)
        cfg = open(self._instroot + "/etc/sysconfig/mkinitrd", "w")
        cfg.write(mkinitrd)
        cfg.close()
                       
    
    #
    # Actual implementation
    #
    def _mount_instroot(self, base_on = None):
        self.__imgdir = self._mkdtemp()
        
        #list of partitions from kickstart file
        parts = self.ks.handler.partition.partitions
        
        #list of disks where a disk is an dict with name: and size
        disks = []

        for i in range(len(parts)):
            disk = parts[i].disk
            size =   parts[i].size * 1024L * 1024L
            
            if len(disks) == 0:
                disks.append({ 'name': disk, 'size': size })
            else:
                found = 'false' 
                for j in range(len(disks)):
                    if disks[j]['name'] == disk:
                        disks[j]['size'] = disks[j]['size'] + size
                        found = 'true'
                        break
                    else: found = 'false'
                if found == 'false':
                    disks.append({ 'name': disk, 'size': size })    
            
                        
        #create disk
        for item in disks:
            logging.debug("Adding disk %s as %s/disk-%s.raws" % (item['name'], self.__imgdir, item['name']))
            disk = SparseLoopbackDisk("%s/disk-%s.raw" % (self.__imgdir, item['name']),item['size'])
            self.__disks[item['name']] = disk

        self.__instloop = PartitionedMount(self.__disks,
                                           self._instroot)

        for p in parts:
            self.__instloop.add_partition(int(p.size), p.disk, p.mountpoint, p.fstype)

        try:
            self.__instloop.mount()
        except MountError, e:
            raise CreatorError("Failed mount disks : %s" % e)
        
        self._create_mkinitrd_config()


    def _get_required_packages(self):
        return ["grub"]

    def _create_grub_devices(self):
        devs = []
        parts = self.ks.handler.partition.partitions
        for p in parts:
            dev = p.disk
            if not dev in devs:
                devs.append(dev)

        devs.sort()

        n = 0
        devmap = ""
        for dev in devs:
            devmap += "(hd%-d) /dev/%s\n" % (n, dev)
            n += 1

        logging.debug("Writing grub %s/boot/grub/device.map" % self._instroot)
        cfg = open(self._instroot + "/boot/grub/device.map", "w")
        cfg.write(devmap)
        cfg.close()

    def _get_grub_boot_config(self):
        bootdevnum = None
        rootdevnum = None
        rootdev = None
        for p in self.__instloop.partitions:
            if p['mountpoint'] == "/boot":
                bootdevnum = p['num'] - 1
            elif p['mountpoint'] == "/" and bootdevnum is None:
                bootdevnum = p['num'] - 1

            if p['mountpoint'] == "/":
                rootdevnum = p['num'] - 1
                rootdev = "/dev/%s%-d" % (p['disk'], p['num'])

        prefix = ""
        if bootdevnum == rootdevnum:
            prefix = "/boot"

        return (bootdevnum, rootdevnum, rootdev, prefix)

    def _create_grub_config(self):
        (bootdevnum, rootdevnum, rootdev, prefix) = self._get_grub_boot_config()
        options = self.ks.handler.bootloader.appendLine

        # NB we're assuming that grub config is on the first physical disk
        # ie /boot must be on sda, or if there's no /boot, then / must be sda

        # XXX don't hardcode default kernel - see livecd code
        grub = ""
        grub += "default=0\n"
        grub += "timeout=5\n"
        grub += "splashimage=(hd0,%d)%s/grub/splash.xpm.gz\n" % (bootdevnum, prefix)
        grub += "hiddenmenu\n"
        
        versions = []
        kernels = self._get_kernel_versions()
        for kernel in kernels:
            for version in kernels[kernel]:
                versions.append(version)

        for v in versions:
            grub += "title %s (%s)\n" % (self.name, v)
            grub += "        root (hd0,%d)\n" % bootdevnum
            grub += "        kernel %s/vmlinuz-%s ro root=%s %s\n" % (prefix, v, rootdev, options)
            grub += "        initrd %s/initrd-%s.img\n" % (prefix, v)

        logging.debug("Writing grub config %s/boot/grub/grub.conf" % self._instroot)
        cfg = open(self._instroot + "/boot/grub/grub.conf", "w")
        cfg.write(grub)
        cfg.close()

    def _copy_grub_files(self):
        imgpath = None
        for machine in ["x86_64-redhat", "i386-redhat"]:
            imgpath = self._instroot + "/usr/share/grub/" + machine
            if os.path.exists(imgpath):
                break

        files = ["e2fs_stage1_5", "stage1", "stage2"]
        for f in files:
            path = imgpath + "/" + f
            if not os.path.isfile(path):
                raise CreatorError("grub not installed : "
                                   "%s not found" % path)

            logging.debug("Copying %s to %s/boot/grub/%s" %(path, self._instroot, f))
            shutil.copy(path, self._instroot + "/boot/grub/" + f)

    def _install_grub(self):
        (bootdevnum, rootdevnum, rootdev, prefix) = self._get_grub_boot_config()

        # Ensure all data is flushed to disk before doing grub install
        subprocess.call(["sync"])

        stage2 = self._instroot + "/boot/grub/stage2"

        setup = ""
        #for i in range(len(self.__disks)):
        i = 0
        for name in self.__disks.keys():
            loopdev = self.__disks[name].device
            setup += "device (hd%s) %s\n" % (i,loopdev)
            i =i+1
        setup += "root (hd0,%d)\n" % bootdevnum
        setup += "setup --stage2=%s --prefix=%s/grub  (hd0)\n" % (stage2, prefix)
        setup += "quit\n"

        logging.debug("Installing grub to %s" % loopdev)
        grub = subprocess.Popen(["grub", "--batch", "--no-floppy"],
                                stdin=subprocess.PIPE)
        grub.communicate(setup)
        rc = grub.wait()
        if rc != 0:
            raise MountError("Unable to install grub bootloader")

    def _create_bootconfig(self):
        self._create_grub_devices()
        self._create_grub_config()
        self._copy_grub_files()
        self._install_grub()

    def _unmount_instroot(self):
        if not self.__instloop is None:
            self.__instloop.cleanup()

    def _resparse(self, size = None):
        return self.__instloop.resparse(size)


    def _write_image_xml(self):
        xml = "<image>\n"
        xml += "  <name>%s</name>\n" % self.name
        xml += "  <domain>\n"
        # XXX don't hardcode - determine based on the kernel we installed for grub
        # baremetal vs xen
        xml += "    <boot type='hvm'>\n"
        xml += "      <guest>\n"
        xml += "        <arch>%s</arch>\n" % os.uname()[4]
        xml += "      </guest>\n"
        xml += "      <os>\n"
        xml += "        <loader dev='hd'/>\n"
        xml += "      </os>\n"
        #for i in range(len(self.__disks)):
        i = 0
        for name in self.__disks.keys():
            xml += "      <drive disk='%s-%s.%s' target='hd%s'/>\n" % (self.name,name, self.__format,chr(ord('a')+i))
            i = i + 1
        xml += "    </boot>\n"
        xml += "    <devices>\n"
        xml += "      <vcpu>%s</vcpu>\n" % self.__vcpu 
        xml += "      <memory>%d</memory>\n" %(self.__vmem * 1024)
        xml += "      <interface/>\n"
        xml += "      <graphics/>\n"
        xml += "    </devices>\n"
        xml += "  </domain>\n"
        xml += "  <storage>\n"
        #for i in range(len(self.__disks)):
        for name in self.__disks.keys():
            # XXX don't hardcode raw
            xml += "    <disk file='%s-%s.%s' use='system' format='%s'/>\n" % (self.name,name, self.__format, self.__format)
        xml += "  </storage>\n"
        xml += "</image>\n"

        logging.debug("writing image XML to %s/%s.xml" %  (self._outdir, self.name))
        cfg = open("%s/%s.xml" % (self._outdir, self.name), "w")
        cfg.write(xml)
        cfg.close()
        

    def _stage_final_image(self):
        self._resparse()

        self._write_image_xml()
        logging.debug("moving disks to final location")
        for name in self.__disks.keys():
            dst = "%s/%s-%s.%s" % (self._outdir, self.name,name, self.__format)
            if self.__format == "raw":
                logging.debug("moving %s image to %s " % (self.__disks[name].lofile, dst))
                shutil.move(self.__disks[name].lofile, dst)
            else:
                logging.debug("converting %s image to %s" % (self.__disks[name].lofile, dst))
                rc = subprocess.call(["qemu-img", "convert",
                                      "-f", "raw", self.__disks[name].lofile,
                                      "-O", self.__format,  dst])
                if rc != 0:
                    raise CreatorError("Unable to convert disk to %s" % (self.__format))
