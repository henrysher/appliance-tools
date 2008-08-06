# Kickstart file to build the thincrust appliance 
# operating system for Fedora 9

lang C
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
bootloader --timeout=1 --append="acpi=force"
network --bootproto=dhcp --device=eth0 --onboot=on
# Root password is thincrust
rootpw --iscrypted $1$uw6MV$m6VtUWPed4SqgoW6fKfTZ/

# 
# Partitoin Information. Change this as necessary
#
part / --size 500 --fstype ext3 --ondisk sda

#
# Repositories
#
repo --name=f9 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-9&arch=$basearch
repo --name=f9-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f9&arch=$basearch

#
# Add all the packages after the base packages
#
%packages --excludedocs --nobase
	%include base-pkgs.ks
%end

#
# Add custom post scripts after the base post.
# 
%post
	#%include base-post.ks
%end
