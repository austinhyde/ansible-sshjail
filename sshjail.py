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

    def get_jail_path(self):
        code, _, stdout, stderr = self._exec_command(' '.join(['jls', '-j', self.jname, '-q', 'path']))
        # remove \n
        return stdout.strip().split('\n')[-1]

    def get_jail_id(self):
        if self.jid == None:
            code, _, stdout, stderr = self._exec_command(' '.join(['jls', '-j', self.jname, '-q', 'jid']))
            # remove \n
            self.jid = stdout.strip().split('\n')[-1]
        return self.jid

    def get_tmp_file(self):
        code, _, stdout, stderr = self._exec_command('mktemp', '', None)
        return stdout.strip().split('\n')[-1]


    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):
        self.host = host
        jaildef, self.jailhost = host.split('@',1)
        self.jname = re.sub(r'\W','_',jaildef)
        self.runner = runner
        self.has_pipelining = False
        self.ssh = SSHConn(runner, self.jailhost, port, user, password, private_key_file, *args)
        self.jid = None
        self.juser = None

    def connect(self, port=None):
        self.ssh.connect();
        return self

    def _exec_command(self, cmd, tmp_path='', become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        # oh lordy I hate this approach, but we need to note what user we use to access the jail so put/fetch works
        if become_user != None:
            self.juser = become_user

        return self.ssh.exec_command(cmd, tmp_path, become_user, sudoable, executable, in_data)


    def exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        ''' run a command in the jail '''

        if SSHJAIL_USE_JAILME:
            jcmd = ['jailme', self.get_jail_id()]
        else:
            jcmd = ['jexec', self.jname]

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

        code, _, stdout, stderr = self._exec_command(' '.join(['chmod 0777',tmp]))
        if code != 0:
            raise errors.AnsibleError("failed to make temp file %s world writable:\n%s\n%s" % (tmp, stdout, stderr))

        code, _, stdout, stderr = self._exec_command(' '.join(['cp',tmp,out_path]), '', self.juser, True)
        if code != 0:
            raise errors.AnsibleError("failed to move file from %s to %s:\n%s\n%s" % (tmp, out_path, stdout, stderr))

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote jail to local '''
        tmp = self.get_tmp_file()
        in_path = self._normalize_path(in_path, self.get_jail_path())
        self._exec_command(' '.join(['mv',in_path,tmp]), '', self.juser, True)
        self.ssh.fetch_file(tmp, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass
