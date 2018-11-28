#!/usr/bin/env python3
from osmo_gsm_tester.testenv import *

def print_results(cli_res, srv_res):
    cli_sent = cli_res['end']['sum_sent']
    cli_recv = cli_res['end']['sum_received']
    print("RESULT client:")
    print("\tSEND: %d KB, %d kbps, %d seconds (%d retrans)" % (cli_sent['bytes']/1000, cli_sent['bits_per_second']/1000,  cli_sent['seconds'], cli_sent['retransmits']))
    print("\tRECV: %d KB, %d kbps, %d seconds" % (cli_recv['bytes']/1000, cli_recv['bits_per_second']/1000, cli_recv['seconds']))
    print("RESULT server:")
    print("\tSEND: %d KB, %d kbps, %d seconds" % (cli_sent['bytes']/1000, cli_sent['bits_per_second']/1000, cli_sent['seconds']))
    print("\tRECV: %d KB, %d kbps, %d seconds" % (cli_recv['bytes']/1000, cli_recv['bits_per_second']/1000, cli_recv['seconds']))

def run_iperf3_cli_parallel(iperf3clients, ms_li):
    assert len(iperf3clients) == len(ms_li)
    procs = []
    for i in range(len(iperf3clients)):
        print("Running iperf3 client to %s through %r" % (str(iperf3clients[i]), repr(ms_li[i].tmp_ctx_id)))
        procs.append(iperf3clients[i].prepare_test_proc(ms_li[i].netns()))
    try:
        for proc in procs:
            proc.launch()
        for proc in procs:
            proc.wait()
    except Exception as e:
        for proc in procs:
            proc.terminate()
        raise e


def setup_run_iperf3_test_parallel(num_ms):
    hlr = suite.hlr()
    bts = suite.bts()
    pcu = bts.pcu()
    mgw_msc = suite.mgw()
    mgw_bsc = suite.mgw()
    stp = suite.stp()
    ggsn = suite.ggsn()
    sgsn = suite.sgsn(hlr, ggsn)
    msc = suite.msc(hlr, mgw_msc, stp)
    bsc = suite.bsc(msc, mgw_bsc, stp)

    iperf3srv_addr = suite.ip_address()
    servers = []
    clients = []
    ms_li = []
    for i in range(num_ms):
        iperf3srv = suite.iperf3srv(iperf3srv_addr)
        iperf3srv.set_port(iperf3srv.DEFAULT_SRV_PORT + i)
        servers.append(iperf3srv)

        iperf3cli = iperf3srv.create_client()
        clients.append(iperf3cli)

        ms = suite.modem()
        ms_li.append(ms)

    bsc.bts_add(bts)
    sgsn.bts_add(bts)

    for iperf3srv in servers:
        print('start iperfv3 server %s...' % str(iperf3srv) )
        iperf3srv.start()

    print('start network...')
    hlr.start()
    stp.start()
    ggsn.start()
    sgsn.start()
    msc.start()
    mgw_msc.start()
    mgw_bsc.start()
    bsc.start()

    bts.start()
    wait(bsc.bts_is_connected, bts)
    print('Waiting for bts to be ready...')
    wait(bts.ready_for_pcu)
    pcu.start()

    for ms in ms_li:
        hlr.subscriber_add(ms)
        ms.connect(msc.mcc_mnc())
        ms.attach()
        ms.log_info()

    print('waiting for modems to attach...')
    for ms in ms_li:
        wait(ms.is_connected, msc.mcc_mnc())
    wait(msc.subscriber_attached, *ms_li)

    print('waiting for modems to attach to data services...')
    for ms in ms_li:
        wait(ms.is_attached)
        # We need to use inet46 since ofono qmi only uses ipv4v6 eua (OS#2713)
        ctx_id_v4 = ms.activate_context(apn='inet46', protocol=ms.CTX_PROT_IPv4)
        print("Setting up data plan for %r" % repr(ctx_id_v4))
        ms.setup_context_data_plane(ctx_id_v4)
        setattr(ms, 'tmp_ctx_id', ctx_id_v4)

    run_iperf3_cli_parallel(clients, ms_li)

    for i in range(num_ms):
        servers[i].stop()
        print("Results for %s through %r" % (str(servers[i]), repr(ms_li[i].tmp_ctx_id)))
        print_results(clients[i].get_results(), servers[i].get_results())

    for ms in ms_li:
        ms.deactivate_context(ms.tmp_ctx_id)
        delattr(ms, 'tmp_ctx_id')