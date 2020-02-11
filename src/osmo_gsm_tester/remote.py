# osmo_gsm_tester: specifics for remote nodes
#
# Copyright (C) 2020 by sysmocom - s.f.m.c. GmbH
#
# Author: Pau Espin Pedrol <pespin@sysmocom.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import stat
import os
import re
import pprint

from . import log, util, config, template, process, osmo_ctrl, pcap_recorder

class RemoteHost(log.Origin):

    WRAPPER_SCRIPT = 'ssh_sigkiller.sh'

    def __init__(self, run_dir, remote_user = 'root', remote_host = 'localhost', remote_cwd=None):
        super().__init__(log.C_RUN, 'host-' + remote_user + '@' + remote_host)
        self.run_dir = util.Dir(run_dir.new_dir(self.name()))
        self.remote_user = remote_user
        self.remote_host = remote_host
        self.remote_cwd = remote_cwd
        self.remote_env = {}

    def user(self):
        return self.remote_user

    def host(self):
        return self.remote_host

    def cwd(self):
        return self.remote_cwd

    def set_remote_env(self, remote_env_dict):
        self.remote_env = remote_env_dict

    def get_remote_env(self):
        return self.remote_env

    def RemoteProcess(self, name, popen_args, remote_env={}, **popen_kwargs):
        run_dir = self.run_dir.new_dir(name)
        return process.RemoteProcess(name, run_dir, self.user(), self.host(), self.cwd(), popen_args, remote_env=remote_env, **popen_kwargs)

    def generate_wrapper_script(self):
        wrapper_script = self.run_dir.new_file(RemoteHost.WRAPPER_SCRIPT)
        with open(wrapper_script, 'w') as f:
            r = """#!/bin/bash
            mypid=0
            sign_handler() {
                    sig=$1
                    echo "received signal handler $sig, killing $mypid"
                    kill $mypid
            }
            trap 'sign_handler SIGTERM' SIGTERM
            trap 'sign_handler SIGINT' SIGINT
            trap 'sign_handler SIGHUP' SIGHUP
            $@ &
            mypid=$!
            echo "waiting for $mypid"
            wait $mypid
            echo "process $mypid finished"
            """
            f.write(r)
        st = os.stat(wrapper_script)
        os.chmod(wrapper_script, st.st_mode | stat.S_IEXEC)
        return wrapper_script

    def RemoteProcessFixIgnoreSIGHUP(self, name, remote_dir, popen_args, remote_env={}, **popen_kwargs):
        # Run remotely through ssh. We need to run binary under a wrapper
        # script since osmo-trx ignores SIGHUP and will keep running after
        # we close local ssh session. The wrapper script catches SIGHUP and
        # sends SIGINT to it.
        self.create_remote_dir(remote_dir)

        wrapper_script = self.generate_wrapper_script()
        remote_wrapper_script = remote_dir.child(RemoteHost.WRAPPER_SCRIPT)
        self.scp('scp-wrapper-to-remote', wrapper_script, remote_wrapper_script)

        args = (remote_wrapper_script,) + popen_args
        return self.RemoteProcess(name, args, remote_env, **popen_kwargs)

    def run_remote_sync(self, name, popen_args):
        proc = self.RemoteProcess(name, popen_args, remote_env=self.remote_env)
        proc.launch_sync()
        return proc

    def rm_remote_dir(self, remote_dir):
        remote_dir_str = str(remote_dir)
        self.run_remote_sync('rm-remote-dir', ('test', '!', '-d', remote_dir_str, '||', 'rm', '-rf', remote_dir_str))

    def create_remote_dir(self, remote_dir):
        remote_dir_str = str(remote_dir)
        self.run_remote_sync('mk-remote-dir', ('mkdir', '-p', remote_dir_str))

    def recreate_remote_dir(self, remote_dir):
        self.rm_remote_dir(remote_dir)
        self.create_remote_dir(remote_dir)

    def inst_compatible_for_remote(self):
        proc = self.run_remote_sync('uname-m', ('uname', '-m'))
        if "x86_64" in (proc.get_stdout() or ''):
            return True
        return False

    def scp(self, name, local_path, remote_path):
        process.run_local_sync(self.run_dir, name, ('scp', '-r', local_path, '%s@%s:%s' % (self.user(), self.host(), remote_path)))
