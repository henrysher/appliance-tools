# Kickstart file to build the appliance operating
# system for fedora9.
# This is based on the work at http://www.thincrust.net
lang C
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --permissive
firewall --disabled
bootloader --timeout=1 --append="acpi=force console=ttyS0,115200"
network --bootproto=dhcp --device=eth0 --onboot=on
services --enabled=network

# Uncomment the next line
# to make the root password be thincrust
# By default the root password is emptied
#rootpw --iscrypted $1$uw6MV$m6VtUWPed4SqgoW6fKfTZ/

#add virtio modules
device virtio_blk
device virtio_pci
device xennet
device xenblk

#
# Partition Information. Change this as necessary
# This information is used by appliance-tools but
# not by the livecd tools.
#
part / --size 750 --fstype ext3 --ondisk hda

#
# Repositories
# repo --name=rhel --baseurl=http://path/to/your/rhel/repo/RHEL-5-Server/U3/x86_64/os/Server/
repo --name=rhel5.3 --baseurl=http://porkchop.devel.redhat.com/released/RHEL-5-Server/U3-Beta/x86_64/os/Server/

#
# Add all the packages after the base packages
#
%packages --excludedocs --nobase
bash
kernel
kernel-xen
grub
e2fsprogs
passwd
policycoreutils
chkconfig
rootfiles
yum
vim-minimal
acpid

#Allow for dhcp access
dhclient
iputils

#
# Packages to Remove
#

# no need for kudzu if the hardware doesn't change
-kudzu
-prelink
-setserial
-ed

# Remove the authconfig pieces
-authconfig
-rhpl
-wireless-tools

# Remove the kbd bits
-kbd
-usermode

# these are all kind of overkill but get pulled in by mkinitrd ordering
-mkinitrd
-kpartx
-dmraid
-mdadm
-lvm2
-tar

# selinux toolchain of policycoreutils, libsemanage, ustr
-policycoreutils
-checkpolicy
-selinux-policy*
-libselinux-python
-libselinux


%end

#
# Add custom post scripts after the base post.
#
%post

%end

