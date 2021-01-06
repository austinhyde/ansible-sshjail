#!/usr/local/bin/bash
set -e

# https://github.com/freebsd/pkg/issues/1526
# pkg is broken as of 1.9.4_1 on FreeBSD 10.1, need to manually fix
# portsnap fetch
# portsnap extract ports-mgmt/
# portsnap extract Mk/
# portsnap extract distfiles


# this also fails with
#   policykit-0.9_8: missing file /usr/local/etc/PolicyKit/PolicyKit.conf.dist
#   pkg-static: Fail to set time on /var/run/PolicyKit:No such file or directory
# but everything seems to work without it for now, so just ||true
# pkg upgrade --yes

# pkg install --yes lang/python