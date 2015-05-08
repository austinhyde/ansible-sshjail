# ansible-sshjail

An Ansible connection plugin for remotely provisioning FreeBSD jails separately from their jailhost.

This works by SSHing to the jail host using the standard Ansible SSH connection, moving any files into the jail directory, and using jexec to execute commands in the scope of the jail.

# Requirements

Control node (your workstation or deployment server):

* Ansible
* Python 2.7

Jailhost:

* FreeBSD
* At least one configured jail
* Python 2.7
* SSH
* sudo

Target jail:

* Python 2.7

# Installation

This is a "Connection Type Plugin", as outlined in the [Ansible docs](http://docs.ansible.com/developing_plugins.html#connection-type-plugins).

To install sshjail:

1. Clone this repo.
2. Copy or link `sshjail.py` to one of the supported locations:
  * `/usr/share/ansible/plugins/connection_plugins/sshjail.py`
  * `path/to/your/toplevelplaybook/connection_plugins/sshjail.py`

# Usage

Using sshjail, each jail is its own inventory host, identified with a host name of `jailname[:jailuser]@jailhost`. You must also specify `ansible_connection=sshjail`.

* `jailname` is the name of the jail. Typically jails are referred to by their hostname, like `my-db-jail`, but the actual name of the jail (by default) would be `my_db_jail`. sshjail will attempt to convert any non-word characters (`[^a-zA-Z0-9_]`) to underscores for the purposes of referring to jails by their actual name.
* `jailuser` is a user that is allowed to drop into that jail. If not specified, this is assumed to be `root`.
* `jailhost` is the hostname or IP address of the jailhost.

Also note that FreeBSD pkgng places Python at `/usr/local/bin/python2.7` by default. Make sure to specify this with the `ansible_python_interpreter` variable!

The following inventory entries are examples of using sshjail:

```
# bare minimum
my-db-jail@192.168.1.100 ansible_python_interpreter=/usr/local/bin/python2.7 ansible_connection=sshjail

# sample vagrant configuration
my-db-jail ansible_ssh_host=my-db-jail@127.0.0.1 ansible_ssh_port=2222 ansible_python_interpreter=/usr/local/bin/python2.7 ansible_connection=sshjail ansible_ssh_user=vagrant
```

Adding these hosts dynamically, like after freshly creating them via Ansible, or by iterating over `jls` output, can be done via the [built-in `add_host` module](http://docs.ansible.com/add_host_module.html):

```YAML
- name: add my-db-jail to ansible inventory
  add_host: name=my-db-jail groups=jails
            ansible_ssh_host=my-db-jail@{{ansible_ssh_host}}
            ansible_ssh_port={{ansible_ssh_port}}
            ansible_python_interpreter=/usr/local/bin/python2.7
            ansible_connection=sshjail
```

# Known Issues

* Outside of a playbook (like via the `ansible` command), you must use the `-b` option to use remote-sudo
* Inside of a playbook, it is very hard to read. Just kidding, you need `sudo: yes` for any tasks targeting jails
* Fetching files hasn't been tested yet. It may not work.
* Error handling within the plugin needs improved. At the moment, it appears that any permission issues are being reported with odd error messages. Use verbose output (`-vvvv`) and open an issue if you run into this!

# Contributing

Let me know if you have any difficulties using this, by creating an issue.

Pull requests are always welcome! I'll try to get them reviewed in a timely manner.
