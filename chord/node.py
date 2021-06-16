import math
import pprint
import statistics

from sortedcontainers import SortedDict

from util import generate_keys
from hash import hash_value, NUM_BITS

pp = pprint.PrettyPrinter()


class Node:

    def __init__(self, name, id):
        self.name = name
        self.digest_id = id
        self.successor = None
        self.fingers = []

    def get_name(self):
        return self.name

    def successor(self):
        return self.successor

    def get_id(self):
        return self.digest_id

    def set_successor(self, successor):
        self.successor = successor

    def fix_fingers(self):
        i = 0
        next_key = self.digest_id + pow(2, i)
        while i < NUM_BITS:
            next_finger = self.find_successor(next_key, 0)[0]
            self.fingers.append(next_finger)

            i += 1
            next_key = self.digest_id + pow(2, i)

    def find_successor(self, digest, hops):
        next_id = self.successor.get_id()
        if next_id > self.digest_id:
            if self.digest_id < digest <= next_id:
                return self.successor, hops
            else:
                return self.successor.find_successor(digest, hops + 1)
        else:
            # Handle the case where this node has the highest digest
            if digest > self.digest_id or digest <= next_id:
                return self.successor, hops
            else:
                return self.successor.find_successor(digest, hops + 1)


class ChordNode(Node):

    def find_successor(self, digest, hops):
        if digest == self.digest_id:
            return self

        next_id = self.successor.get_id()
        if next_id > self.digest_id:
            if self.digest_id < digest <= next_id:
                return self.successor, hops
            else:
                next_node = self.closest_preceding_node(digest)
                return next_node.find_successor(digest, hops + 1)
        else:
            # Handle the case where this node has the highest digest
            if digest > self.digest_id or digest <= next_id:
                return self.successor, hops
            else:
                next_node = self.closest_preceding_node(digest)
                return next_node.find_successor(digest, hops + 1)

    def closest_preceding_node(self, digest):
        for i in range(start=NUM_BITS - 1, stop=0):
            if self.digest_id < digest:
                if self.digest_id < self.fingers[i].get_id() < digest:
                    return self.fingers[i]
            elif self.digest_id > digest:
                if (self.digest_id < self.fingers[i].get_id()
                        or self.fingers[i].get_id() < digest):
                    return self.fingers[i]
            else:
                # We shouldn't get here but we could return predecessor here to be safe
                pass


def build_nodes(num_nodes):
    node_name_fmt = "node_{id}"
    node_ids = SortedDict()

    for i in range(num_nodes):
        name = node_name_fmt.format(id=str(i))
        digest = hash_value(name)
        node_ids[digest] = name

    # List of nodes to return
    nodes = []

    # Create the last node first and set it to prev_node so that successor
    # is set correctly
    last_digest = node_ids.keys()[-1]
    last_name = node_ids.values()[-1]
    last_node = Node(last_name, last_digest)
    prev_node = last_node

    # Iterate through sorted node ids to create nodes and set the successors
    for node_id in node_ids.keys()[:-1]:
        next_node = Node(node_ids[node_id], node_id)
        prev_node.set_successor(next_node)
        prev_node = next_node
        nodes.append(next_node)

    next_node.set_successor(last_node)
    nodes.append(last_node)

    for node in nodes:
        node.fix_fingers()

    return nodes


def run_experiment(num_nodes, num_keys):
    nodes = build_nodes(num_nodes)
    keys = generate_keys(num_keys)

    hops_tracker = []
    starting_node = nodes[0]
    for key in keys:
        node, hops = starting_node.find_successor(hash_value(key), 0)
        hops_tracker.append(hops)

    return statistics.mean(hops_tracker)


def main():
    # ----------------------------------------------------
    # Test naive routing
    # ----------------------------------------------------
    print("\nCalculating average hops for naive routing...\n")
    num_nodes = 50
    num_keys = 100
    avg_hops = run_experiment(num_nodes, num_keys)
    print(f"Average hops with {num_nodes} nodes is {avg_hops}")

    assert math.isclose(avg_hops, 22.38, abs_tol=0.01)

    num_nodes = 100
    avg_hops = run_experiment(num_nodes, num_keys)
    print(f"Average hops with {num_nodes} nodes is {avg_hops}")

    assert avg_hops == 40

    # The number of hops to find a key using naive routing should be
    # proportional to the number of nodes in the network. Specifically
    # it should be close to n/2 which is what we see here

    # ----------------------------------------------------
    # Test finger table
    # ----------------------------------------------------
    print("\nBuild network...\n")
    nodes = build_nodes(10)
    node_table = [{"id": node.get_id(), "name": node.get_name()} for node in nodes]
    pp.pprint({"network": node_table})

    assert nodes[0].get_id() == 24 and nodes[0].get_name() == "node_3"
    assert nodes[1].get_id() == 32 and nodes[1].get_name() == "node_2"
    assert nodes[2].get_id() == 46 and nodes[2].get_name() == "node_6"
    assert nodes[3].get_id() == 109 and nodes[3].get_name() == "node_4"
    assert nodes[4].get_id() == 145 and nodes[4].get_name() == "node_8"
    assert nodes[5].get_id() == 150 and nodes[5].get_name() == "node_7"
    assert nodes[6].get_id() == 160 and nodes[6].get_name() == "node_0"
    assert nodes[7].get_id() == 163 and nodes[7].get_name() == "node_1"
    assert nodes[8].get_id() == 241 and nodes[8].get_name() == "node_9"
    assert nodes[9].get_id() == 244 and nodes[9].get_name() == "node_5"

    print("\nRetrieve finger table...\n")
    test_node = nodes[0]
    fingers = test_node.fingers
    finger_table = [{"position": i, "id": finger.get_id(), "name": finger.get_name()}
                    for i, finger in enumerate(fingers)]
    pp.pprint({"name": test_node.get_name(), "id": test_node.get_id(), "fingers": finger_table})

    assert fingers[0].get_id() == 32 and fingers[0].get_name() == "node_2"
    assert fingers[1].get_id() == 32 and fingers[1].get_name() == "node_2"
    assert fingers[2].get_id() == 32 and fingers[2].get_name() == "node_2"
    assert fingers[3].get_id() == 32 and fingers[3].get_name() == "node_2"
    assert fingers[4].get_id() == 46 and fingers[4].get_name() == "node_6"
    assert fingers[5].get_id() == 109 and fingers[5].get_name() == "node_4"
    assert fingers[6].get_id() == 109 and fingers[6].get_name() == "node_4"
    assert fingers[7].get_id() == 160 and fingers[7].get_name() == "node_0"


if __name__ == "__main__":
    main()
