%{!?python_sitelib: %define python_sitelib %(%{__python} -c "import distutils.sysconfig as d; print d.get_python_lib()")}

%define debug_package %{nil}

Summary: Tools for building Appliances
Name: appliance-tools
Version: 002.20
Release: 1%{?dist}
License: GPLv2
Group: System Environment/Base
URL: http://thincrust.net
# The source for this package was pulled from upstream's vcs.  Use the
# following commands to generate the tarball:
#  git clone git://git.et.redhat.com/act.git; cd act 
#  git archive --format=tar --prefix=appliance-tools-%{version} appliance-tools-%{version} | bzip2 > appliance-tools-%{version}.tar.bz2
Source0: %{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: livecd-tools >= 020 curl rsync kpartx
Requires: zlib
#Requires: qemu-img
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
%doc config/fedora9-aos.ks
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
* Wed Jan 14 2009 David Huff <dhuff@redhat.com> - 002.20
- ported for epel build 

* Tue Dec 02 2008 David Huff <dhuff@redhat.com> - 002.8-2
- changed form ExclusiveArch to EcludeArch to fix broken deps

* Mon Nov 17 2008 David Huff <dhuff@redhat.com> - 002.8
- backported fix for bug that causes appliance-creator to stacktrace when -i is omitted (pmyers)

* Fri Nov 14 2008 David Huff <dhuff@redhat.com> - 002.7
- backported Fixed bug that causes appliance-creator to stacktrace when -i is omitted (pmyers)

* Wed Nov 13 2008 David Huff <dhuff@redhat.com> - 002.6
- backported Fix for problem with -i only taking one file
- Fixed versioning of source file

* Fri Nov 07 2008 David Huff <dhuff@redhat.com> - 002-5
- Fixed broken dependencies for specific archs where qemu is not available
- backported ec2 converter code (jboggs)
- backported features form applaince-tools-003-5
-- Fixed problem with long move operations (#466278)
-- Fixed error converting disk formats (#464798)
-- Added support for tar archives (#470292)
-- Added md5/sha256 disk signature support (jboggs)
-- Modified zip functionality can now do with or with out 64bit ext.
-- Added support for including extra file in the package (#470337)
-- Added option for -o outdir, no longer uses name
-- OutPut is now in a seprate dir under appliance name

* Mon Oct 13 2008 David Huff <dhuff@redhat.com> 002-4
- fix for problem with long move operations (#466278)
- support patterns in directory names (apevec)
- fix exit upon error when converting disk formats (#464798)

* Wed Sep 24 2008 David Huff <dhuff@redhat.com> 002-3
- refactored code to match upsteaem project
- backported new features from upsteam version 003-4

* Wed Jul 09 2008 Alan Pevec <apevec@redhat.com> 002-1
- import imgcreate.fs refactoring and other changes
  to make it work with Fedora-9 livecd-tools-0.17.1 w/o Thincrust patches

* Wed Jun 11 2008 David Huff <dhuff@redhat.com> - 001-3
- fixed dependancys

* Tue Jun 10 2008 David Huff <dhuff@redhat.com> - 001-2
- Undated opt parser
- fixed grub issue
- build aginsted newer livecd-tools for selinux issues

* Wed May 14 2008 David Huff <dhuff@redhat.com> - 001
- Initial build.

