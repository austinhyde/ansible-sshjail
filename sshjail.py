import distutils.spawn
import traceback
import os
import shutil
import subprocess
import re
import sys
from ansible import errors
from ansible.callbacks import vvv
import ansible.constants as C
from ansible.runner.connection_plugins.ssh import Connection as SSHConn

SSHJAIL_USE_JAILME = False

class Connection(object):
    ''' jail-over-ssh based connections '''

    def match_jail(self):
        if self.jid == None:
            code, _, stdout, stderr = self._exec_command("jls -q jid name host.hostname path")
            if code != 0:
                vvv("JLS stdout: %s" % stdout)
                raise errors.AnsibleError("jls returned non-zero!")

            lines = stdout.strip().split('\n')
            found = False
            for line in lines:
                jid, name, hostname, path = line.strip().split()
                if name == self.jailspec or hostname == self.jailspec:
                    self.jid = jid
                    self.jname = name
                    self.jhost = hostname
                    self.jpath = path
                    found = True
                    break

            if not found:
                raise errors.AnsibleError("failed to find a jail with name or hostname of '%s'" % self.jailspec)

    def get_jail_path(self):
        self.match_jail()
        return self.jpath

    def get_jail_id(self):
        self.match_jail()
        return self.jid

    def get_tmp_file(self):
        code, _, stdout, stderr = self._exec_command('mktemp', '', None)
        return stdout.strip().split('\n')[-1]


    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):
        # my-jail@my.jailhost => my-jail is jail name/hostname, my.jailhost is jailhost hostname
        self.host = host
        self.jailspec, self.jailhost = host.split('@',1)

        # piggyback off of the standard SSH connection
        self.runner = runner
        self.has_pipelining = False
        self.ssh = SSHConn(runner, self.jailhost, port, user, password, private_key_file, *args)

        # jail information loaded on first use by match_jail
        self.jid = None
        self.jname = None
        self.jhost = None
        self.jpath = None

    def connect(self, port=None):
        self.ssh.connect();
        return self

    # runs a command on the jailhost, rather than inside the jail
    def _exec_command(self, cmd, tmp_path='', become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        return self.ssh.exec_command(cmd, tmp_path, become_user, sudoable, executable, in_data)


    def exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        ''' run a command in the jail '''

        if SSHJAIL_USE_JAILME:
            jcmd = ['jailme', self.get_jail_id()]
        else:
            jcmd = ['jexec', self.get_jail_id()]

        if executable:
            local_cmd = ' '.join([jcmd[0], jcmd[1], executable, '-c', '"%s"' % cmd])
        else:
            local_cmd = '%s "%s" "%s"' % (jcmd[0], jcmd[1], cmd)

        vvv("JAIL (%s) %s" % (become_user, local_cmd), host=self.host)
        return self._exec_command(local_cmd, tmp_path, become_user, True, executable, in_data)

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote jail '''
        tmp = self.get_tmp_file()
        self.ssh.put_file(in_path, tmp)
        out_path = self._normalize_path(out_path, self.get_jail_path())

        code, _, stdout, stderr = self._exec_command(' '.join(['chmod 0644',tmp]))
        if code != 0:
            raise errors.AnsibleError("failed to make temp file %s world readable:\n%s\n%s" % (tmp, stdout, stderr))

        code, _, stdout, stderr = self._exec_command(' '.join(['cp',tmp,out_path]), '', self.runner.become_user, True)
        if code != 0:
            raise errors.AnsibleError("failed to move file from %s to %s:\n%s\n%s" % (tmp, out_path, stdout, stderr))

        code, _, stdout, stderr = self._exec_command(' '.join(['rm',tmp]))
        if code != 0:
            raise errors.AnsibleError("failed to remove temp file %s:\n%s\n%s" % (tmp, stdout, stderr))

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote jail to local '''
        tmp = self.get_tmp_file()
        in_path = self._normalize_path(in_path, self.get_jail_path())
        self._exec_command(' '.join(['mv',in_path,tmp]), '', self.juser, True)
        self.ssh.fetch_file(tmp, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass
