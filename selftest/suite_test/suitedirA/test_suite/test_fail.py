#!/usr/bin/env python3
from osmo_gsm_tester.testenv import *

print('I am %r / %r' % (tenv.suite().name(), test.name()))

test.set_fail('EpicFail', 'This failure is expected')
