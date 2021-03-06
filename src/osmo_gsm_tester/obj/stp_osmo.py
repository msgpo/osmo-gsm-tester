# osmo_gsm_tester: specifics for running an osmo-stp
#
# Copyright (C) 2017 by sysmocom - s.f.m.c. GmbH
#
# Author: Neels Hofmeyr <neels@hofmeyr.de>
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

import os
import pprint

from ..core import log, util, config, template, process
from . import pcap_recorder

class OsmoStp(log.Origin):

    def __init__(self, testenv, ip_address):
        super().__init__(log.C_RUN, 'osmo-stp_%s' % ip_address.get('addr'))
        self.run_dir = None
        self.config_file = None
        self.process = None
        self.testenv = testenv
        self.ip_address = ip_address

    def start(self):
        self.log('Starting osmo-stp')
        self.configure()

        inst = util.Dir(os.path.abspath(self.testenv.suite().trial().get_inst('osmo-stp')))

        binary = inst.child('bin', 'osmo-stp')
        if not os.path.isfile(binary):
            raise RuntimeError('Binary missing: %r' % binary)
        lib = inst.child('lib')
        if not os.path.isdir(lib):
            raise RuntimeError('No lib/ in %r' % inst)

        pcap_recorder.PcapRecorder(self.testenv, self.run_dir.new_dir('pcap'), None,
                                   'host %s and port not 22' % self.addr())

        env = { 'LD_LIBRARY_PATH': util.prepend_library_path(lib) }

        self.dbg(run_dir=self.run_dir, binary=binary, env=env)
        self.process = process.Process(self.name(), self.run_dir,
                                       (binary, '-c',
                                        os.path.abspath(self.config_file)),
                                       env=env)
        self.testenv.remember_to_stop(self.process)
        self.process.launch()

    def configure(self):
        self.run_dir = util.Dir(self.testenv.test().get_run_dir().new_dir(self.name()))
        self.config_file = self.run_dir.new_file('osmo-stp.cfg')
        self.dbg(config_file=self.config_file)

        values = dict(stp=config.get_defaults('stp'))
        config.overlay(values, self.testenv.suite().config())
        config.overlay(values, dict(stp=dict(ip_address=self.ip_address)))

        self.dbg('STP CONFIG:\n' + pprint.pformat(values))

        with open(self.config_file, 'w') as f:
            r = template.render('osmo-stp.cfg', values)
            self.dbg(r)
            f.write(r)

    def conf_for_client(self):
        return dict(stp=dict(ip_address=self.ip_address))

    def addr(self):
        return self.ip_address.get('addr')

    def running(self):
        return not self.process.terminated()

# vim: expandtab tabstop=4 shiftwidth=4
