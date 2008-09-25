%{!?python_sitelib: %define python_sitelib %(%{__python} -c "import distutils.sysconfig as d; print d.get_python_lib()")}

%define debug_package %{nil}

Summary: Tools for building Appliances
Name: appliance-tools
Version: 002
Release: 3%{?dist}
License: GPLv2
Group: System Environment/Base
URL: http://thincrust.net
Source0: %{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: livecd-tools >= 017.1
Requires: zlib
Requires: qemu-img
BuildRequires: python
BuildArch: noarch


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
%dir %{python_sitelib}/appcreate
%{python_sitelib}/appcreate/*.py
%{python_sitelib}/appcreate/*.pyo
%{python_sitelib}/appcreate/*.pyc

%changelog
* Wed Sep 24 2008 David Huff <dhuff@redhat.com> 002-2
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

