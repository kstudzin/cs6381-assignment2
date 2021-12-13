import argparse
import random
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
import zmq

from node import RoutingInfo, FindSuccessorCommand

default_trials = 1000
empty_routing_info = RoutingInfo(address='')
url = "http://204.236.223.42:30495/api/v1/query?query=avg(sum_over_time(kube_pod_status_phase{phase=\"Running\", namespace='chord'}[3h]) * 3 * 30)"


def wait_for_response(receiver):
    event = receiver.poll(2 * 1000, zmq.POLLIN)
    if event == zmq.POLLIN:
        return receiver.recv_pyobj().recipient
    else:
        return empty_routing_info


def config_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--search')
    parser.add_argument('bootstrap_endpoint')
    parser.add_argument('runtime')
    parser.add_argument('--id', default=256)
    parser.add_argument('--port', default='5550')

    return parser


def get_average_session(runtime_seconds):
    response = requests.request("GET", url)
    return float(response.data.result.value[1])


def main():
    parser = config_parser()
    args = parser.parse_args()

    bootstrap_endpoint = args.bootstrap_endpoint
    id = int(args.id)
    port = args.port
    runtime = datetime.strptime(args.runtime, '%H:%M:%S,%f')
    runtime_seconds = runtime.second + runtime.minute * 60 + runtime.hour * 3600

    if args.search:
        search_term = int(args.search)
        random_search = False
        num_trials = 1
    else:
        search_term = None
        random_search = True
        num_trials = default_trials

    bootstrap_id = 1
    endpoint = f'tcp://{socket.gethostbyname(socket.gethostname())}:{port}'

    # Start dealer waiting
    print('Creating ZMQ Context')
    context = zmq.Context()

    identity = struct.pack('i', id)
    receiver = context.socket(zmq.DEALER)
    receiver.setsockopt(zmq.LINGER, 0)
    receiver.setsockopt(zmq.IDENTITY, identity)
    receiver.bind(endpoint)

    # ZMQ sockets
    print('Creating router socket')
    router = context.socket(zmq.ROUTER)
    router.connect(bootstrap_endpoint)
    time.sleep(1)

    print('Creating thread pool executor')
    executor = ThreadPoolExecutor()

    # Find successor command
    me = RoutingInfo(address=endpoint, digest=id, parent_digest=id)
    cn = RoutingInfo(address=bootstrap_endpoint, digest=bootstrap_id, parent_digest=bootstrap_id)

    print('Running tests...')
    file = open('times.csv', 'w')
    init_time = time.time()
    curr_time = init_time
    i = 0
    while curr_time < init_time + runtime_seconds:
        future = executor.submit(wait_for_response, receiver=receiver)
        time.sleep(1)

        if i % 100 == 0:
            print(f'Elapsed time: {curr_time - init_time} of {runtime_seconds} seconds')

        # print('Creating find successor command')
        if random_search:
            search_term = random.randrange(0, 255)
        cmd = FindSuccessorCommand(initiator=me, recipient=cn, search_digest=search_term)

        # Send message
        # print(f'Chord Node: {bootstrap_endpoint} ({bootstrap_id})')
        print(f'Command: {cmd}')
        start = time.time()
        router.send(struct.pack('i', bootstrap_id), zmq.SNDMORE)
        router.send_pyobj(cmd)

        # Wait for response
        # print('Waiting on future')
        result = future.result()
        end = time.time()

        if result.digest:
            csv = f'{search_term},{result.digest},{result.address},{end - start}\n'
        else:
            csv = f'{search_term},{result.digest},{result.address},\n'

        print(csv)
        file.write(csv)

        i += 1
        curr_time = time.time()

    avg_session = get_average_session(runtime_seconds)
    print(f'Average session time: {avg_session}')

    file.close()
    executor.shutdown()


if __name__ == '__main__':
    main()
