# Copyright (c) 2018, NVIDIA CORPORATION. All rights reserved.
# See file LICENSE for terms.
#
# Description: Check bandwidth between client and server. Execution
# command must specify if the benchmark is run intra-node.

import ucp
import time
import argparse
import asyncio
import concurrent.futures

accept_cb_started = False
new_client_ep = None
max_msg_log = 23
max_iters = 256
window_size = 64

async def talk_to_client(client_ep):

    global args

    msg_log = max_msg_log
    iters = max_iters
    comm_ep = client_ep

    send_buffer_region = ucp.buffer_region()
    recv_buffer_region = ucp.buffer_region()

    if args.mem_type == 'cuda':
        send_buffer_region.alloc_cuda(1 << msg_log)
        recv_buffer_region.alloc_cuda(1 << msg_log)
    else:
        send_buffer_region.alloc_host(1 << msg_log)
        recv_buffer_region.alloc_host(1 << msg_log)

    print("{}\t\t{}".format("Size (bytes)", "Bi-Bandwidth (GB/s)"))

    for i in range(msg_log):
        msg_len = 2 ** i

        warmup_iters = int((0.1 * iters))
        for j in range(warmup_iters):
            pending_list = []
            for k in range(window_size):
                send_msg = ucp.ucp_msg(send_buffer_region)
                recv_msg = ucp.ucp_msg(recv_buffer_region)
                send_ft = comm_ep.send(send_msg, msg_len)
                recv_ft = comm_ep.recv(recv_msg, msg_len)
                pending_list.append(send_ft)
                pending_list.append(recv_ft)
            await asyncio.wait(pending_list)

        start = time.time()
        for j in range(iters):
            pending_list = []
            for k in range(window_size):
                send_msg = ucp.ucp_msg(send_buffer_region)
                recv_msg = ucp.ucp_msg(recv_buffer_region)
                send_ft = comm_ep.send(send_msg, msg_len)
                recv_ft = comm_ep.recv(recv_msg, msg_len)
                pending_list.append(send_ft)
                pending_list.append(recv_ft)
            await asyncio.wait(pending_list)
        end = time.time()
        lat = end - start
        bw = (iters * window_size * msg_len * 2) / lat
        bw = bw / 1e9 #GB/s
        print("{}\t\t{}".format(msg_len, bw))

    if args.mem_type == 'cuda':
        send_buffer_region.free_cuda()
        recv_buffer_region.free_cuda()
    else:
        send_buffer_region.free_host()
        recv_buffer_region.free_host()

    ucp.destroy_ep(client_ep)
    ucp.stop_server()

async def talk_to_server(ip, port):

    global args

    msg_log = max_msg_log
    iters = max_iters

    server_ep = ucp.get_endpoint(ip, port)
    comm_ep = server_ep

    send_buffer_region = ucp.buffer_region()
    recv_buffer_region = ucp.buffer_region()

    if args.mem_type == 'cuda':
        send_buffer_region.alloc_cuda(1 << msg_log)
        recv_buffer_region.alloc_cuda(1 << msg_log)
    else:
        send_buffer_region.alloc_host(1 << msg_log)
        recv_buffer_region.alloc_host(1 << msg_log)

    for i in range(msg_log):
        msg_len = 2 ** i

        warmup_iters = int((0.1 * iters))
        for j in range(warmup_iters):
            pending_list = []
            for k in range(window_size):
                send_msg = ucp.ucp_msg(send_buffer_region)
                recv_msg = ucp.ucp_msg(recv_buffer_region)
                send_ft = comm_ep.send(send_msg, msg_len)
                recv_ft = comm_ep.recv(recv_msg, msg_len)
                pending_list.append(send_ft)
                pending_list.append(recv_ft)
            await asyncio.wait(pending_list)

        start = time.time()
        for j in range(iters):
            pending_list = []
            for k in range(window_size):
                send_msg = ucp.ucp_msg(send_buffer_region)
                recv_msg = ucp.ucp_msg(recv_buffer_region)
                send_ft = comm_ep.send(send_msg, msg_len)
                recv_ft = comm_ep.recv(recv_msg, msg_len)
                pending_list.append(send_ft)
                pending_list.append(recv_ft)
            await asyncio.wait(pending_list)
        end = time.time()
        lat = end - start
        lat = ((lat/2) / iters)* 1000000

    if args.mem_type == 'cuda':
        send_buffer_region.free_cuda()
        recv_buffer_region.free_cuda()
    else:
        send_buffer_region.free_host()
        recv_buffer_region.free_host()

    ucp.destroy_ep(server_ep)

parser = argparse.ArgumentParser()
parser.add_argument('-s','--server', help='enter server ip', required=False)
parser.add_argument('-p','--port', help='enter server port number', required=False)
parser.add_argument('-i','--intra_node', action='store_true')
parser.add_argument('-m','--mem_type', help='host/cuda (default = host)', required=False)
args = parser.parse_args()

## initiate ucp
init_str = ""
server = False
if args.server is None:
    server = True
else:
    server = False
    init_str = args.server

ucp.init()
loop = asyncio.get_event_loop()
# coro points to either client or server-side coroutine
if server:
    if args.intra_node:
        ucp.set_cuda_dev(1)
    coro = ucp.start_server(talk_to_client, is_coroutine = True)
else:
    coro = talk_to_server(init_str.encode(), int(args.port))

loop.run_until_complete(coro)

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

loop.close()
