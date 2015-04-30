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
import ansible.runner.connection_plugins.ssh as SSH

class Connection(object):
    ''' jail-over-ssh based connections '''

    def get_jail_path(self):
        code, _, stdout, stderr = self._exec_command(' '.join(['jls', '-j', self.jname, '-q', 'path']), '', 'root');
        # remove \n
        return stdout.strip().split('\n')[-1]
 
        
    def __init__(self, runner, host, port, user, password, private_key_file, *args, **kwargs):
        self.realhost = host
        self.jname, self.host = host.split('@',1)
        self.jname = re.sub(r'\W','_',self.jname)
        self.runner = runner
        self.has_pipelining = False
        self.ssh = SSH.Connection(runner, self.host, port, user, password, private_key_file, *args)

    def connect(self, port=None):
        self.ssh.connect();
        return self

    def _exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        vvv("JEXEC %s" % (cmd), host=self.realhost)
        sys.stdin.readline()
        return self.ssh.exec_command(cmd, tmp_path, 'root', True, executable, in_data)


    def exec_command(self, cmd, tmp_path, become_user=None, sudoable=False, executable='/bin/sh', in_data=None):
        ''' run a command on the chroot '''

        if executable:
            local_cmd = ' '.join(['jexec', self.jname, executable, '-c', '"%s"' % cmd])
        else:
            local_cmd = 'jexec "%s" "%s"' % (self.jname, cmd)

        return self._exec_command(local_cmd, tmp_path, become_user, sudoable, executable, in_data)

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def put_file(self, in_path, out_path):
        ''' transfer a file from local to remote jail '''
        out_path = self._normalize_path(out_path, self.get_jail_path())
        print out_path
        self.ssh.put_file(in_path, out_path)

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote jail to local '''
        in_path = self._normalize_path(in_path, self.get_jail_path())
        self.ssh.fetch_file(in_path, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass
