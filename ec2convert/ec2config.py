#!/usr/bin/python -tt
#
# ec2config.py: Convert a virtual appliance image in an EC2 AMI
#
# Copyright 2008, Red Hat  Inc.
# Joseph Boggs <jboggs@redhat.com>
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
import sys
import logging
    
class ec2_modify:
    
    def makedev(self,tmpdir):
        os.popen("/sbin/MAKEDEV -d %s/dev -x console" % tmpdir)
        os.popen("/sbin/MAKEDEV -d %s/dev -x null" % tmpdir)
        os.popen("/sbin/MAKEDEV -d %s/dev -x zero" % tmpdir)

    def fstab(self,tmpdir):
        logging.info("* - Updating /etc/fstab")
        fstab_path = tmpdir + "/etc/fstab"
        os.system("touch " + fstab_path)
        fstab = open(fstab_path, "w")
        ec2_fstab =  "/dev/sda1  /         ext3    defaults        1 1\n"
        ec2_fstab += "/dev/sda2  /mnt      ext3    defaults        1 2\n"
        ec2_fstab += "/dev/sda3  swap      swap    defaults        0 0\n"
        ec2_fstab += "none       /dev/pts  devpts  gid=5,mode=620  0 0\n"
        ec2_fstab += "none       /dev/shm  tmpfs   defaults        0 0\n"
        ec2_fstab += "none       /proc     proc    defaults        0 0\n"
        ec2_fstab += "none       /sys      sysfs   defaults        0 0\n"
        fstab.writelines(ec2_fstab)
        fstab.close()


    def rclocal_config(self,tmpdir):
        rclocal_path = tmpdir + "/etc/rc.local"
        rclocal = open(rclocal_path, "w")
        logging.info("* - Creating rc.local configuration\n")
        ec2_rclocal = "if [ ! -d /root/.ssh ] ; then\n"
        ec2_rclocal += "mkdir -p /root/.ssh\n"
        ec2_rclocal += "chmod 700 /root/.ssh\n"
        ec2_rclocal += "fi\n\n"
        ec2_rclocal += " # Fetch public key using HTTP\n"
        ec2_rclocal += "curl -f http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key > /tmp/my-key\n"
        ec2_rclocal += "if [ $? -eq 0 ] ; then\n"
        ec2_rclocal += "cat /tmp/my-key >> /root/.ssh/authorized_keys\n"
        ec2_rclocal += "chmod 600 /root/.ssh/authorized_keys\n"
        ec2_rclocal += "rm /tmp/my-key\n"
        ec2_rclocal += "fi\n\n"
        ec2_rclocal += "# or fetch public key using the file in the ephemeral store:\n"
        ec2_rclocal += "if [ -e /mnt/openssh_id.pub ] ; then\n"
        ec2_rclocal += "cat /mnt/openssh_id.pub >> /root/.ssh/authorized_keys\n"
        ec2_rclocal += "chmod 600 /root/.ssh/authorized_keys\n"
        ec2_rclocal += "fi\n\n"
        ec2_rclocal += "# Update the EC2 AMI creation tools\n"
        ec2_rclocal += "echo Updating ec2-ami-tools\n"
        ec2_rclocal += "curl -o /tmp/ec2-ami-tools.noarch.rpm http://s3.amazonaws.com/ec2-downloads/ec2-ami-tools.noarch.rpm && \n"
        ec2_rclocal += "rpm -Uvh /tmp/ec2-ami-tools.noarch.rpm && \n"
        ec2_rclocal += "echo \" + Updated ec2-ami-tools\"\n"
        rclocal.writelines(ec2_rclocal)
        rclocal.close()    

    def ssh_config(self,tmpdir):
        try: 
            sshdconfig_path = tmpdir + "/etc/ssh/sshd_config"
            sshdconfig = open(sshdconfig_path,"w")
        except IOError, (errno, strerror):
            logging.error( "%s, %s" % (strerror,sshdconfig_path))
            logging.error( "The openssh_server package must be installed to convert and function properly on EC2" )
            sys.exit(1)
        else:
            logging.info("* - Creating ssh configuration")
            ec2_sshdconfig = "UseDNS  no\n"
            ec2_sshdconfig +="PermitRootLogin without-password\n"
            sshdconfig.writelines(ec2_sshdconfig)
            sshdconfig.close()    

    def eth0_config(self,tmpdir):
        try: 
            logging.info("* - Creating eth0 configuration")
            eth0_path = tmpdir + "/etc/sysconfig/network-scripts/ifcfg-eth0"
            os.system("touch %s" % eth0_path)
            eth0 = open(eth0_path, "w")
        except IOError, (errno, strerror):
            logging.info( "%s, %s" % (strerror,eth0_path) )
            sys.exit(1)
        else:
            ec2_eth0 = "ONBOOT=yes\n"
            ec2_eth0 += "DEVICE=eth0\n"
            ec2_eth0 += "BOOTPROTO=dhcp\n"
            eth0.writelines(ec2_eth0)
            eth0.close()
            os.system("chroot %s /sbin/chkconfig network on" % tmpdir)
        
        logging.info("* - Prevent nosegneg errors")
        os.system("echo \"hwcap 0 nosegneg\" > %s/etc/ld.so.conf.d/nosegneg.conf" % tmpdir)    
    
    def ami_tools(self,tmpdir):
        logging.info("Adding EC2 Tools")
        
        if os.path.isdir(tmpdir + "/home/ec2"): 
            pass
        else:
            os.mkdir(tmpdir + "/home/ec2")
            
        ec2td = os.system("curl -o /tmp/ec2-api-tools-1.2-9739.zip http://s3.amazonaws.com/ec2-downloads/ec2-api-tools-1.2-9739.zip")
        if ec2td == 0:
            os.system("unzip -qo /tmp/ec2-api-tools-1.2-9739.zip -d /home/ec2")
        else:
            logging.error( "EC2 tools download error!")
            sys.exit(1)
            
    
    def kernel_modules(self,tmpdir):    
        logging.info("Configure image for accepting the EC2 kernel")
    
        kd = os.system("curl -o /tmp/kernel-xen-2.6.21.7-2.fc8.i686.rpm http://kojipkgs.fedoraproject.org/packages/kernel-xen-2.6/2.6.21.7/2.fc8/i686/kernel-xen-2.6.21.7-2.fc8.i686.rpm")
        if kd == 0:
            os.system("rpm -ivh --nodeps /tmp/kernel-xen-2.6.21.7-2.fc8.i686.rpm --root=%s" % tmpdir)
        else:
            logging.error("Kernel download error!")

