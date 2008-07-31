# from katzj's appliance creator script
# cut locale archive down to a smaller set; this should be handled 
# automatically based on %packages --installLangs once that's supported
localedef --list-archive |grep -v en_US | xargs localedef --delete-from-archive
mv /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive.tmpl
/usr/sbin/build-locale-archive

# remove some things that mkinitrd doesn't really need in this case
# we should probably find a way to remove the deps and still have
# ordering work properly
rpm -e --nodeps mkinitrd kpartx dmraid mdadm lvm2 tar

# fedora-release-notes is required by fedora-release and is pretty 
# large, but not really needed for an appliance
rpm -e --nodeps fedora-release-notes

# here, remove a bunch of files we don't need that are just eating up space.
# it breaks rpm slightly, but it's not too bad

# FIXME: ug, hard-coded paths.  This is going to break if we change to F-9
# or upgrade certain packages.  Not quite sure how to handle it better

# Added from pmyers image-minimization patch
RM="rm -rf"
# Remove docs and internationalization
$RM /usr/share/omf
$RM /usr/share/gnome
$RM /usr/share/doc
$RM /usr/share/locale
$RM /usr/share/libthai
$RM /usr/share/man
$RM /usr/share/terminfo
$RM /usr/share/X11
$RM /usr/share/i18n

find /usr/share/zoneinfo -regextype egrep -type f ! -regex ".*/EST.*|.*/GMT" -exec $RM {} \;

$RM /usr/lib/locale
$RM /usr/lib/syslinux
$RM /usr/lib64/gconv
$RM /usr/lib64/pango
$RM /usr/lib64/libpango*
$RM /etc/pango
$RM /usr/bin/pango*

# Remove unnecessary kernel modules

MODULES="XXX/lib/modules/*/kernel"
$RM $MODULES/sound

fs_mods="9p affs autofs autofs4 befs bfs cifs coda configfs cramfs dlm \
         ecryptfs efs exportfs freevxfs fuse gfs2 hfs hfsplus jbd jbd2 \
         jffs jfs minix ncpfs ocfs2 qnx4 reiserfs romfs sysv udf ufs xfs"
for dir in $fs_mods ; do
  $RM $MODULES/fs/$dir
done

net_mods="802 8021q 9p appletalk atm ax25 bluetooth dccp decnet \
          ieee80211 ipx irda mac80211 netrom rfkill rose sched \
          sctp tipc wanrouter wireless"
for dir in $net_mods ; do
   $RM $MODULES/net/$dir
done

driver_mods="bluetooth firewire i2c isdn media edac"
for dir in $driver_mods ; do
   $RM $MODULES/drivers/$dir
done


