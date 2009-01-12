%{!?python_sitelib: %define python_sitelib %(%{__python} -c "import distutils.sysconfig as d; print d.get_python_lib()")}

%define debug_package %{nil}

Summary: Tools for building Appliances
Name: appliance-tools
Version: 004
Release: 2%{?dist}
License: GPLv2
Group: System Environment/Base
URL: http://git.et.redhat.com/?p=act.git
# The source for this package was pulled from upstream's vcs.  Use the
# following commands to generate the tarball:
#  git clone git://git.et.redhat.com/act.git; cd act 
#  git archive --format=tar --prefix=appliance-tools-%{version} appliance-tools-%{version} | bzip2 > appliance-tools-%{version}.tar.bz2
Source0: %{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: livecd-tools >= 020 curl rsync kpartx
Requires: zlib
Requires: qemu-img
BuildRequires: python
BuildArch: noarch
ExcludeArch: ppc64 s390 s390x


%description
Tools for generating appliance images on Fedora based systems including
derived distributions such as RHEL, CentOS and others. See
http://thincrust.net for more details.

%prep
%setup -q

%build
make

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README COPYING
%doc config/fedora-aos.ks
%{_mandir}/man*/*
%{_bindir}/appliance-creator
%{_bindir}/image-minimizer
%{_bindir}/ec2-converter
%dir %{python_sitelib}/appcreate
%dir %{python_sitelib}/ec2convert
%{python_sitelib}/appcreate/*.py
%{python_sitelib}/appcreate/*.pyo
%{python_sitelib}/appcreate/*.pyc
%{python_sitelib}/ec2convert/*.py
%{python_sitelib}/ec2convert/*.pyo
%{python_sitelib}/ec2convert/*.pyc

%changelog
*Mon Dec 01 2008 David Huff <dhuff@redhat.com> -004-2
- changed form ExclusiveArch to EcludeArch to fix broken deps

*Mon Dec 01 2008 David Huff <dhuff@redhat.com> - 004
- bumped version for rebuild for Python 2.6
- Allow the user to pass in --version and --release command line paramneters (bkearney)
- Patches to integrate ec2 conversion into the adk (bkeareny)
- Allow the appliance-creator to use remote urls with the new image tools (bkearney)

*Fri Nov 14 2008 David Huff <dhuff@redhat.com> - 003.9
- Fixed bug in globbing files under a directory (pmyers)

*Fri Nov 14 2008 David Huff <dhuff@redhat.com> - 003.8
- Fixed bug that causes appliance-creator to stacktrace when -i is omitted (pmyers)

*Wed Nov 12 2008 David Huff <dhuff@redhat.com> - 003.7
- Fixed problem with -i only taking one file, now can include a dir
- Fixed versioning of source file, ie. 003.7

*Mon Nov 10 2008 David Huff <dhuff@redhat.com> - 003-6
- Fixed broken dependencies for specific archs where qemu is not available

*Fri Nov 07 2008 David Huff <dhuff@redhat.com> - 003-5
- Added error for Incomplete partition info (#465988)
- Fixed problem with long move operations (#466278)
- Fixed error converting disk formats (#464798)
- Added support for tar archives (#470292)
- Added md5/sha256 disk signature support (jboggs)
- Modified zip functionality can now do with or with out 64bit ext.
- Added support for including extra file in the package (#470337)
- Added option for -o outdir, no longer uses name
- OutPut is now in a seprate dir under appliance name

*Wed Sep 17 2008 David Huff <dhuff@redhat.com> - 003-4
- Removed all the kickstart files in the config dir to mirror livecd-tools
- Added the image minimization to the refactored code (BKearney)
- multiple interface issue (#460922)
- added --format option to specity disk image format
- added --package option to specify output, currently only .zip supported
- added --vmem and --vcpu options
- Merged ec2-converter code (jboggs)

*Tue Aug 26 2008 David Huff <dhuff@redhat.com> - 003-3
- release 3 fixes minor build errors 

* Wed Jul 09 2008 David Huff <dhuff@redhat.com> - 003-1
- version 003 is build for latest version of livecd-tools with patches

* Wed Jul 09 2008 Alan Pevec <apevec@redhat.com> 002-1
- import imgcreate.fs refactoring and other changes
  to make it work with Fedora-9 livecd-tools-0.17.1 w/o Thincrust patches
- version 002 is for f9 branch to work with stock f9 livecd-tools

* Wed Jun 11 2008 David Huff <dhuff@redhat.com> - 001-3
- fixed dependancys

* Tue Jun 10 2008 David Huff <dhuff@redhat.com> - 001-2
- Undated opt parser
- fixed grub issue
- build aginsted newer livecd-tools for selinux issues

* Wed May 14 2008 David Huff <dhuff@redhat.com> - 001
- Initial build.


