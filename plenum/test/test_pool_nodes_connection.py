import random
import types
from hashlib import sha256
from time import sleep

from raet.road.transacting import Joiner, Allower, Messenger, Allowent

from ledger.compact_merkle_tree import CompactMerkleTree

from ledger.ledger import Ledger
from plenum.common.config_util import getConfig

from plenum.common.port_dispenser import genHa
from plenum.common.raet import initLocalKeep
from plenum.common.signer_simple import SimpleSigner
from plenum.common.txn import TXN_ID, TARGET_NYM, DATA, NODE, ALIAS, NODE_IP, \
    NODE_PORT, CLIENT_IP, CLIENT_PORT, SERVICES, VALIDATOR
from plenum.common.txn import TYPE
from plenum.common.txn_util import createGenesisTxnFile
from plenum.common.util import randomString
from plenum.test.greek import genNodeNames
from plenum.test.test_node import TestNode
from plenum.test.test_node import checkNodesConnected
from plenum.test.test_node_connection import tdirAndLooper, tdir, looper


whitelist = ['discarding message', 'found legacy entry']


# Joiner.Timeout = 10.0

Allower.Timeout = 20.0
Allower.RedoTimeoutMin = 2 # initial timeout
Allower.RedoTimeoutMax = 8.0 # max timeout

Allowent.Timeout = 20.0
Allowent.RedoTimeoutMin = 2 # initial timeout
Allowent.RedoTimeoutMax = 8.0 # max timeout


def testPoolNodesConnection(tdir, looper):
    """
    7 nodes will start,
    """
    tconf = getConfig(tdir)
    # names = genNodeNames(7)
    names = ['spielen', 'jouer', 'asobi', 'imirt', 'masakmasak', 'majiyan', 'play']
    seeds = []
    has = []
    clihas = []
    txns = []
    nodes = []
    for name in names:
        seed = randomString(32)
        initLocalKeep(name, tdir, seed, override=True)
        ha = genHa()
        cliha = genHa()
        nip, nport = ha
        cip, cport = cliha
        singer = SimpleSigner(seed=seed.encode())
        txns.append({
            TYPE: NODE,
            TXN_ID: sha256(seed.encode()).hexdigest(),
            TARGET_NYM: singer.verkey,
            DATA: {
                ALIAS: name,
                NODE_IP: nip,
                NODE_PORT: nport,
                CLIENT_IP: cip,
                CLIENT_PORT: cport,
                SERVICES: [VALIDATOR, ]
            }
        })
        seeds.append(seed)
        has.append(ha)
        clihas.append(cliha)

    createGenesisTxnFile(txns, tdir, tconf.poolTransactionsFile, reset=True)

    delays = [0+random.random() for _ in range(len(names))]
    random.shuffle(delays)

    for i, name in enumerate(names):
        node = TestNode(name, nodeRegistry=None, basedirpath=tdir, ha=has[i],
                        cliha=clihas[i])
        nodes.append(node)

    def patch():
        for i in range(len(nodes)):
            node = nodes[i]
            old = node.nodestack.server.send

            def p(old):
                def send(self, data, da):
                    print(
                        '{} will delay all sends by {}'.format(self, delays[i]))
                    sleep(delays[i])
                    old(data, da)
                return send

            send = p(old)
            node.nodestack.server.send = types.MethodType(send,
                                                          node.nodestack.server)

    patch()
    orders = list(range(len(names)))
    random.shuffle(orders)

    for i in orders:
        s = random.randint(2, 4)
        sleep(s)
        print('Starting {} after sleeping for {}'.format(nodes[i], s))
        looper.add(nodes[i])

    print('All nodes should be ready now')

    # looper.run()
    looper.run(checkNodesConnected(nodes,
                                   overrideTimeout=300))
