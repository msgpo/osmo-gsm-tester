#!/usr/bin/env python3
from osmo_gsm_tester.testenv import *

hlr = suite.hlr()
bts = suite.bts()
mgw_msc = suite.mgw()
mgw_bsc = suite.mgw()
stp = suite.stp()
msc = suite.msc(hlr, mgw_msc, stp)
bsc = suite.bsc(msc, mgw_bsc, stp)
ms = suite.modem()

print('start network...')
msc.set_authentication(False)
msc.set_encryption('a5_0')
bsc.set_encryption('a5_0')
hlr.start()
stp.start()
msc.start()
mgw_msc.start()
mgw_bsc.start()
bsc.bts_add(bts)
bsc.start()
bts.start()
wait(bsc.bts_is_connected, bts)

ms.log_info()
good_ki = ms.ki()
bad_ki = ("%1X" % (int(good_ki[0], 16) ^ 0x01)) + good_ki[1:]

print('KI changed: ' + good_ki + " => " + bad_ki)
ms.set_ki(bad_ki)
hlr.subscriber_add(ms)
print('Attempt connection with wrong KI, should work as it is not used...')
ms.connect(msc.mcc_mnc())
wait(ms.is_connected, msc.mcc_mnc())
wait(msc.subscriber_attached, ms)