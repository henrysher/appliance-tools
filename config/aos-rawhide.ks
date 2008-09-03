#version=RawHide
repo --name=rawhide --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=rawhide&arch=$basearch
# Root password
rootpw --iscrypted $1$uw6MV$m6VtUWPed4SqgoW6fKfTZ/
# Firewall configuration
firewall --disabled
# Network information
network  --bootproto=dhcp --device=eth0 --onboot=on
# System authorization information
auth --useshadow --enablemd5
# System keyboard
keyboard us
# System language
lang C
# SELinux configuration
selinux --disabled

# System timezone
timezone  US/Eastern
# System bootloader configuration
bootloader --append="acpi=force" --location=mbr --timeout=1
# Disk partitioning information
part /  --fstype="ext3" --ondisk=sda --size=500 --bytes-per-inode=4096

%post
        #%include base-post.ks
%end

%packages --excludedocs --nobase
@core
kernel
rootfiles
grub
vim-minimal
passwd
iputils
acpid
e2fsprogs
lokkit
yum
dhclient
chkconfig
bash
-wireless-tools
-kpartx
-kudzu
-lvm2
-ed
-kbd
-authconfig
-setserial
-fedora-release-notes
-prelink
-selinux-policy*
-usermode
-checkpolicy
-dmraid
-tar
-mdadm
-fedora-logos
-mkinitrd
-libselinux-python
-rhpl
-libselinux
-policycoreutils

%end

