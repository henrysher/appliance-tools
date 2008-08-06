VERSION = 003

INSTALL = /usr/bin/install -c
INSTALL_PROGRAM = ${INSTALL}
INSTALL_DATA = ${INSTALL} -m 644
INSTALL_SCRIPT = ${INSTALL_PROGRAM}

INSTALL_PYTHON = ${INSTALL} -m 644
define COMPILE_PYTHON
	python -c "import compileall as c; c.compile_dir('$(1)', force=1)"
	python -O -c "import compileall as c; c.compile_dir('$(1)', force=1)"
endef
PYTHONDIR := $(shell python -c "import distutils.sysconfig as d; print d.get_python_lib()")

all: 

install:
	$(INSTALL_PROGRAM) -D tools/appliance-creator $(DESTDIR)/usr/bin/appliance-creator
	$(INSTALL_DATA) -D README $(DESTDIR)/usr/share/doc/appliance-tools-$(VERSION)/README
	$(INSTALL_DATA) -D COPYING $(DESTDIR)/usr/share/doc/appliance-tools-$(VERSION)/COPYING
	mkdir -p $(DESTDIR)/usr/share/appliance-tools/
	$(INSTALL_DATA) -D config/*.ks $(DESTDIR)/usr/share/appliance-tools/
	mkdir -p $(DESTDIR)/$(PYTHONDIR)/appcreate
	$(INSTALL_PYTHON) -D appcreate/*.py $(DESTDIR)/$(PYTHONDIR)/appcreate/
	$(call COMPILE_PYTHON,$(DESTDIR)/$(PYTHONDIR)/appcreate)

uninstall:
	rm -f $(DESTDIR)/usr/bin/appliance-creator
	rm -rf $(DESTDIR)/usr/lib/appliance-creator
	rm -rf $(DESTDIR)/usr/share/doc/appliance-tools-$(VERSION)
	rm -rf $(DESTDIR)/usr/share/appliance-tools

dist : all
	git-archive --format=tar --prefix=appliance-tools-$(VERSION)/ HEAD | bzip2 -9v > appliance-tools-$(VERSION).tar.bz2

clean:
	rm -f *~ creator/*~ installer/*~ config/*~

