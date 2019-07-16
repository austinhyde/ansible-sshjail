# ansible-sshjail

[![GitHub release](https://img.shields.io/github/release/austinhyde/ansible-sshjail.svg?style=flat-square)](https://github.com/austinhyde/ansible-sshjail/releases)

An Ansible connection plugin for remotely provisioning FreeBSD jails separately from their jailhost.

This works by SSHing to the jail host using the standard Ansible SSH connection, moving any files into the jail directory, and using jexec to execute commands in the scope of the jail.

# Requirements

Control node (your workstation or deployment server):

* Ansible 2.0 RC3+
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

Using sshjail, each jail is its own inventory host, identified with a host name of `jail@jailhost`. You must also specify `ansible_connection=sshjail`.

* `jail` is the name or hostname of the jail.
* `jailhost` is the hostname or IP address of the jailhost.

Keep in mind that `ezjail` encourages creating jails with their hostname, which implicitly names the jail with underscores substituted for dashes and dots. For example, a jail created with `ezjail-admin create test-jail 'em1|192.168.33.20'`, will have hostname `test-jail` and jail name `test_jail`. sshjail will accept either name in the ansible host specification.

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

## A note about privileges

By default in FreeBSD, only root can enter jails. This means that when invoking `ansible` or `ansible-playbook`,
you need to specify `--become`, and in a playbook, use `become: yes`/`become_method: sudo`. If sudo requires a password
(shame on you if not, unless it's vagrant!), you'll need `--ask-become-pass` as well.

This means any commands executed by sshjail roughly translate to `sudo jexec $jailName $command`.

An alternative to requiring root access is to use the [`jailme`](http://www.freshports.org/sysutils/jailme) utility.
`jailme` is "a setuid version of jexec to allow normal users access to FreeBSD jails".

Another alternavite to requering root acces is to use the [`iocage`](https://www.freshports.org/sysutils/iocage/) utility.
`iocage` is a "jail/container manager amalgamating some of the bestfeatures and technologies the FreeBSD operating system has to offer"

If you want to use `jailme` or `iocage`, you'll need to ensure it's installed on the jailhost, and specify the user to `sudo` as
via `--become-user` on the command line, or `become_user: username` in a play or task. sshjail will prefer to use `jailme`
if it's installed, whether you are sudoing as root or not.

This results in commands similar to `sudo -u $becomeUser jailme $jailId $command`.

Because of limitations of Ansible, this plugin cannot really do things like `sudo jexec sudo -u myuser $command`

# Known Issues

* Fetching files hasn't been tested yet. It may not work.

# Contributing

Let me know if you have any difficulties using this, by creating an issue.

Pull requests are always welcome! I'll try to get them reviewed in a timely manner.
