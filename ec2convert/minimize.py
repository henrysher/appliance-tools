#!/usr/bin/python 
#
# Minimize Appliance images through blacklisting/whitelisting
#
# Copyright 2008  Red Hat, Inc.
# Joey Boggs <jboggs@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.



import sys
import os
from optparse import OptionParser, OptionValueError

def parse_args():
    parser = OptionParser()
    parser.set_usage("%prog DROP:/tmp/directory")
    (options,args) = parser.parse_args()
    if len(args) < 1:
        parser.error(("You need to provide a directory to delete (DELETE:/tmp/directory)"))
    options.image  = args[0]
    return options


def drop(dir):
    print dir

#    options = parse_args()
#    for arg in sys.argv:
#       if arg.startswith("DROP:"):
#           delete, dir = arg.split("DROP:", 1)
#           os.system("rm -rf %s" % dir)
#    else:
#        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit, e:
        sys.exit(e.code)
    except KeyboardInterrupt, e:
        print >> sys.stderr, _("Aborted at user request")
    except Exception, e:
        sys.exit(1)
