This directory contains code necessary to start up a freebsd/centos development environment for ansible-sshjail

To run, simply `vagrant up`.

This creates two virtual machines: `jailhost` and `bootstrap`. The bootstrap VM gets ansible installed on it, and SSHs to the jailhost VM to configure it, using ansible-sshjail.

Code here is based on and trimmed down from https://github.com/nkiraly/koadstation/tree/master/webdevj1

To re-run ansible playbooks, use `vagrant provision bootstrap`.

The ansible command used is, more or less,

```
ansible-playbook -i "$JAILHOST," configure-jailhost.yml
```

The configure-jailhost playbook does the following on the jailhost:

- Install, enable, and configure ezjail, using /opt/jails for its jaildir
- Install a basejail in /opt/jails/basejail
- For every jail defined in jails.yml:
  - Create the named jail with the named ip address(es)
    - In this case, em0 is the NAT interface, em1 is the host-only network
  - Configure jail DNS
  - Install jail rc.conf
  - Start the jail
  - Install pkg, bash, and python inside the jail
  - Add the jail to the current ansible inventory, in the groups listed in the `addhost` field (`redisjails` in this case), using the `sshjail` connection type
- Provisions `redisjails` hosts according to the `redis` role, just like any other ansible role!

You can then verify everything works as expected:

```
$ vagrant ssh jailhost
$ ezjail-admin list
STA JID  IP              Hostname                       Root Directory
--- ---- --------------- ------------------------------ ------------------------
DR  1    10.0.2.22       redis1                         /opt/jails/redis1
    1    em1|10.0.5.22
DR  2    10.0.2.21       redis0                         /opt/jails/redis0
    2    em1|10.0.5.21
$ telnet 10.0.2.22 6379
Trying 10.0.2.22...
Connected to 10.0.2.22.
Escape character is '^]'.
ping
+PONG
set x 10
+OK
get x
$2
10
quit
+OK
$ ^D
```