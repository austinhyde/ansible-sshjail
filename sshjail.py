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

class Connection(object):
    ''' jail-over-ssh based connections '''

    def get_jail_path(self):
        code, _, stdout, stderr = self._exec_command(' '.join(['jls', '-j', self.jname, '-q', 'path']), '', self.jailowner, True)
        # remove \n
        return stdout.strip().split('\n')[-1]

    def get_tmp_file(self):
        code, _, stdout, stderr = self._exec_command('mktemp', '', None)
        return stdout.strip().split('\n')[-1]
 
        
    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):
        self.orighost = host
        jaildef, self.host = host.split('@',1)
        jailowner = 'root'
        if ':' in jaildef:
            jaildef, jailowner = jaildef.split(':', 1)
        self.jname = re.sub(r'\W','_',jaildef)
        self.jailowner = jailowner
        self.runner = runner
        self.has_pipelining = False
        self.ssh = SSHConn(runner, self.host, port, user, password, private_key_file, *args)

    def connect(self, port=None):
        self.ssh.connect();
        return self

    def _exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        # sys.stdin.readline()
        return self.ssh.exec_command(cmd, tmp_path, become_user, sudoable, executable, in_data)


    def exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        ''' run a command in the jail '''

        if executable:
            local_cmd = ' '.join(['jexec', self.jname, executable, '-c', '"%s"' % cmd])
        else:
            local_cmd = 'jexec "%s" "%s"' % (self.jname, cmd)

        vvv("JAIL %s" % (local_cmd), host=self.orighost)
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
        self._exec_command(' '.join(['mv',tmp,out_path]), '', self.jailowner, True)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote jail to local '''
        tmp = self.get_tmp_file()
        in_path = self._normalize_path(in_path, self.get_jail_path())
        self._exec_command(' '.join(['mv',in_path,tmp]), '', self.jailowner, True)
        self.ssh.fetch_file(tmp, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass
