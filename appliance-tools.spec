%{!?python_sitelib: %define python_sitelib %(%{__python} -c "import distutils.sysconfig as d; print d.get_python_lib()")}

%define debug_package %{nil}

Summary: Tools for building Appliances
Name: appliance-tools
Version: 001
Release: thincrust
License: GPLv2
Group: System Environment/Base
URL: http://thincrust.net
Source0: %{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: livecd-tools >= 017
BuildRequires: python


%description 
Tools for generating appliance images on Fedora based systems including
derived distributions such as RHEL, CentOS and others. See
http://thincrust.net for more details.

%prep
%setup -q -n act

%build
make

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README
%doc COPYING
%{_bindir}/appliance-creator
%dir %{_datadir}/appliance-tools
%{_datadir}/appliance-tools/*
%dir %{python_sitelib}/appcreate
%{python_sitelib}/appcreate/*.py
%{python_sitelib}/appcreate/*.pyo
%{python_sitelib}/appcreate/*.pyc

%changelog
* Wed May 14 2008 David Huff <dhuff@redhat.com> - 001
- Initial build.

