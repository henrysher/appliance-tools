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

class ApplianceImageCreator(ImageCreator):
    """Installs a system into a file containing a partitioned disk image.

    ApplianceImageCreator is an advanced ImageCreator subclass; a sparse file
    is formatted with a partition table, each partition loopback mounted
    and the system installed into an virtual disk. The disk image can
    subsequently be booted in a virtual machine or accessed with kpartx

    """

    def __init__(self, ks, name, disks, format="raw"):
        """Initialize a ApplianceImageCreator instance.

        This method takes the same arguments as ImageCreator.__init__()

        """
        ImageCreator.__init__(self, ks, name)

        self.__instloop = None
        self.__imgdir = None
        self.__format = format
        self.__disks = {}
        

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

        s += self._get_fstab_special()
        return s
        
    #
    # Actual implementation
    #
    def _mount_instroot(self, base_on = None):
        self.__imgdir = self._mkdtemp()
        
        #list of partitions from kickstart file
        parts = kickstart.get_partitions(self.ks)
        
        #list of disks where a disk is an dict with name: and size
        disks = []

        for i in range(len(parts)):
            if parts[i].disk is None:
                #default disk sda
                disk = "sda"
            else: disk = parts[i].disk
            if parts[i].size is None:
                #default 4 gig
                size = 4096L * 1024L * 1024L
            else: size =   parts[i].size * 1024L * 1024L
            
            if len(disks) == 0:
                disks.append({ 'name': disk, 'size': size })
            else: 
                for i in range(len(disks)):
                    if disks[i]['name'] == disk:
                        disks[i]['size'] = disks[i]['size'] + size
                    else: disks.append({ 'name': disk, 'size': size })
            
                        
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




    def _get_required_packages(self):
        return ["grub"]

    def _create_grub_devices(self):
        devs = []
        parts = kickstart.get_partitions(self.ks)
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
            grub += "title Fedora (%s)\n" % v
            grub += "        root (hd0,%d)\n" % bootdevnum
            grub += "        kernel %s/vmlinuz-%s ro root=%s\n" % (prefix, v, rootdev)
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
        for i in range(len(self.__disks)):
            loopdev = self.__disks[i]['disk'].device
            setup += "device (hd%d) %s\n" % (i, loopdev)
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
        for i in range(len(self.__disks)):
            xml += "      <drive disk='%s.%s' target='hd%s'/>\n" % (self.__disks[i]['name'], self.__format, chr(ord('a')+i))
        xml += "    </boot>\n"
        xml += "    <devices>\n"
        xml += "      <vcpu>1</vcpu>\n"
        xml += "      <memory>%d</memory>\n" %(256 * 1024)
        xml += "      <interface/>\n"
        xml += "      <graphics/>\n"
        xml += "    </devices>\n"
        xml += "  </domain>\n"
        xml += "  <storage>\n"
        for i in range(len(self.__disks)):
            # XXX don't hardcode raw
            xml += "    <disk file='%s.%s' use='system' format='%s'/>\n" % (self.__disks[i]['name'], self.__format, self.__format)
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
        for i in range(len(self.__disks)):
            dst = "%s/%s.%s" % (self._outdir, self.__disks[i]['name'], self.__format)
            if self.__format == "raw":
                logging.debug("moving %s image to %s " % (self.__disks[i]['disk'].lofile, dst))
                shutil.move(self.__disks[i]['disk'].lofile, dst)
            else:
                logging.debug("converting %s image to %s" % (self.__disks[i]['disk'].lofile, dst))
                rc = subprocess.call(["qemu-img", "convert",
                                      "-f", "raw", self.__disks[i]['disk'].lofile,
                                      "-O", self.__format,  dst])
                if rc != 0:
                    raise CreatorError("Unable to convert disk to %s" % (self.__format))


