#!/bin/bash
set -e

JAILHOST=$1

if ! which ansible-playbook 2>/dev/null; then
  sudo apt-get -y update
  sudo apt-get -y install ansible
  hash -r
fi

# ansible localhost -m yum -a 'name=wget,unzip,zip,python,libselinux-python,git state=present'
chmod 0600 ~/vagrant_insecure_private_key

# for some reason vbox always mounts /vagrant as root+0755, regardless of what we set on it in the vagrantfile
chmod 0777 /vagrant /vagrant/vagrant

cd /vagrant/vagrant

ansible --version

ANSIBLE_HOST_KEY_CHECKING=false ansible-playbook \
  -i "$JAILHOST," \
  --private-key ~/vagrant_insecure_private_key \
  -e ansible_python_interpreter=/usr/local/bin/python2.7 \
  configure-jailhost.yml