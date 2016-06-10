from __future__ import (absolute_import, division, print_function)

import os
import pipes

from ansible.errors import AnsibleError
from ansible.plugins.connection.ssh import Connection as SSHConnection
from contextlib import contextmanager

__metaclass__ = type

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class ConnectionBase(SSHConnection):
    pass


class Connection(ConnectionBase):
    ''' ssh based connections '''

    transport = 'sshjail'

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        # self.host == jailname@jailhost
        self.inventory_hostname = self.host
        self.jailspec, self.host = self.host.split('@', 1)
        # self.jailspec == jailname
        # self.host == jailhost
        # this way SSHConnection parent class uses the jailhost as the SSH remote host

        # jail information loaded on first use by match_jail
        self.jid = None
        self.jname = None
        self.jpath = None
        self.connector = None

        # logging.warning(self._play_context.connection)

    def match_jail(self):
        if self.jid is None:
            code, stdout, stderr = self._jailhost_command("jls -q jid name host.hostname path")
            if code != 0:
                display.vvv("JLS stdout: %s" % stdout)
                raise AnsibleError("jls returned non-zero!")

            lines = stdout.strip().split('\n')
            found = False
            for line in lines:
                if line.strip() == '':
                    break

                jid, name, hostname, path = line.strip().split()
                if name == self.jailspec or hostname == self.jailspec:
                    self.jid = jid
                    self.jname = name
                    self.jpath = path
                    found = True
                    break

            if not found:
                raise AnsibleError("failed to find a jail with name or hostname of '%s'" % self.jailspec)

    def get_jail_path(self):
        self.match_jail()
        return self.jpath

    def get_jail_id(self):
        self.match_jail()
        return self.jid

    def get_jail_connector(self):
        if self.connector is None:
            code, _, _ = self._jailhost_command("which -s jailme")
            if code != 0:
                self.connector = 'jexec'
            else:
                self.connector = 'jailme'
        return self.connector

    def _strip_sudo(self, executable, cmd):
        # Get the command without sudo
        sudoless = cmd.rsplit(executable + ' -c ', 1)[1]
        # Get the quotes
        quotes = sudoless.partition('echo')[0]
        # Get the string between the quotes
        cmd = sudoless[len(quotes):-len(quotes+'?')]
        # Drop the first command becasue we don't need it
        cmd = cmd.split('; ', 1)[1]
        return cmd
        
    def _strip_sleep(self, cmd):        
        # Get the command without sleep
        cmd = cmd.split(' && sleep 0', 1)[0]
        # Add back trailing quote
        cmd = '%s%s' % (cmd, "'")
        return cmd

    def _jailhost_command(self, cmd):
        return super(Connection, self).exec_command(cmd, in_data=None, sudoable=True)

    def exec_command(self, cmd, in_data=None, executable='/bin/sh', sudoable=True):
        slpcmd = ''
        ''' run a command in the jail '''

        if '&& sleep 0' in cmd:
            slpcmd = True
            cmd = self._strip_sleep(cmd)

        if 'sudo' in cmd:
            cmd = self._strip_sudo(executable, cmd)

        cmd = ' '.join([executable, '-c', pipes.quote(cmd)])
        if slpcmd == True:
            cmd = '%s %s %s %s' % (self.get_jail_connector(), self.get_jail_id(), cmd, '&& sleep 0')
        else:
            cmd = '%s %s %s' % (self.get_jail_connector(), self.get_jail_id(), cmd)

        if self._play_context.become:
            # display.debug("_low_level_execute_command(): using become for this command")
            cmd = self._play_context.make_become_cmd(cmd)

        # display.vvv("JAIL (%s) %s" % (local_cmd), host=self.host)
        return super(Connection, self).exec_command(cmd, in_data, True)

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def _copy_file(self, from_file, to_file):
        if self._play_context.become:
            # display.debug("_low_level_execute_command(): using become for this command")
            copycmd = self._play_context.make_become_cmd(' '.join(['cp', from_file, to_file]))

        display.vvv(u"REMOTE COPY {0} TO {1}".format(from_file, to_file), host=self.inventory_hostname)
        code, stdout, stderr = self._jailhost_command(copycmd)
        if code != 0:
            raise AnsibleError("failed to move file from %s to %s:\n%s\n%s" % (from_file, to_file, stdout, stderr))

    @contextmanager
    def tempfile(self):
        code, stdout, stderr = self._jailhost_command('mktemp')
        if code != 0:
            raise AnsibleError("failed to make temp file:\n%s\n%s" % (stdout, stderr))
        tmp = stdout.strip().split('\n')[-1]

        code, stdout, stderr = self._jailhost_command(' '.join(['chmod 0644', tmp]))
        if code != 0:
            raise AnsibleError("failed to make temp file %s world readable:\n%s\n%s" % (tmp, stdout, stderr))

        yield tmp

        code, stdout, stderr = self._jailhost_command(' '.join(['rm', tmp]))
        if code != 0:
            raise AnsibleError("failed to remove temp file %s:\n%s\n%s" % (tmp, stdout, stderr))

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote jail '''
        out_path = self._normalize_path(out_path, self.get_jail_path())

        with self.tempfile() as tmp:
            super(Connection, self).put_file(in_path, tmp)
            self._copy_file(tmp, out_path)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote to local '''
        in_path = self._normalize_path(in_path, self.get_jail_path())

        with self.tempfile() as tmp:
            self._copy_file(in_path, tmp)
            super(Connection, self).fetch_file(tmp, out_path)
