lang C
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
bootloader --timeout=1

part / --size 400 --fstype ext3 --ondisk sda
part /boot --size 300 --fstype ext3 --ondisk sda
