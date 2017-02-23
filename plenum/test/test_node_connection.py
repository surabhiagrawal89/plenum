from random import shuffle, randint

import pytest
from ioflo.aid import getConsole

from plenum.common.eventually import eventually
from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.port_dispenser import genHa
from plenum.common.temp_file_util import SafeTemporaryDirectory
from plenum.common.types import NodeDetail
from plenum.test.helper import stopNodes
from plenum.test.test_node import TestNode, checkNodesConnected, \
    checkProtocolInstanceSetup

logger = getlogger()

whitelist = ['discarding message', 'found legacy entry']


@pytest.fixture()
def nodeReg():
    return {
            'Alpha': NodeDetail(genHa(1), "AlphaC", genHa(1)),
            'Beta': NodeDetail(genHa(1), "BetaC", genHa(1)),
            'Gamma': NodeDetail(genHa(1), "GammaC", genHa(1)),
            'Delta': NodeDetail(genHa(1), "DeltaC", genHa(1))
    }


# Its a function fixture, deliberately
@pytest.yield_fixture()
def tdirAndLooper():
    with SafeTemporaryDirectory() as td:
        logger.debug("temporary directory: {}".format(td))
        with Looper() as looper:
            yield td, looper


@pytest.fixture()
def tdir(tdirAndLooper):
    return tdirAndLooper[0]


@pytest.fixture()
def looper(tdirAndLooper):
    return tdirAndLooper[1]


def testNodesConnectsWhenOneNodeIsLate(allPluginsPath, tdir, looper, nodeReg):
    nodes = []
    names = list(nodeReg.keys())
    logger.debug("Node names: {}".format(names))

    def create(name):
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        looper.add(node)
        node.startKeySharing()
        nodes.append(node)

    for name in names[:3]:
        create(name)

    looper.run(checkNodesConnected(nodes))

    # wait for the election to complete with the first three nodes
    looper.runFor(10)

    # create the fourth and see that it learns who the primaries are
    # from the other nodes
    create(names[3])
    checkProtocolInstanceSetup(looper, nodes, timeout=10)
    stopNodes(nodes, looper)


def testNodesConnectWhenTheyAllStartAtOnce(allPluginsPath, tdir, looper, nodeReg):
    nodes = []
    for name in nodeReg:
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        looper.add(node)
        node.startKeySharing()
        nodes.append(node)
    looper.run(checkNodesConnected(nodes))
    stopNodes(nodes, looper)


# @pytest.mark.parametrize("x10", range(1, 11))
# def testNodesComingUpAtDifferentTimes(x10):
def testNodesComingUpAtDifferentTimes(allPluginsPath, tdir, looper, nodeReg):
    console = getConsole()
    console.reinit(flushy=True, verbosity=console.Wordage.verbose)

    nodes = []

    names = list(nodeReg.keys())
    shuffle(names)
    waits = [randint(1, 10) for _ in names]
    rwaits = [randint(1, 10) for _ in names]

    for i, name in enumerate(names):
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        looper.add(node)
        node.startKeySharing()
        nodes.append(node)
        looper.runFor(waits[i])
        logger.debug('{} started, waiting for {} sec'.format(name, waits[i]))
    looper.run(checkNodesConnected(nodes,
                                   overrideTimeout=10))
    logger.debug("connects")
    logger.debug("node order: {}".format(names))
    logger.debug("waits: {}".format(waits))

    stopNodes(nodes, looper)

    for i, n in enumerate(nodes):
        n.start(looper.loop)
        looper.runFor(rwaits[i])
        logger.debug('{} started, waiting for {} sec'.format(n, rwaits[i]))
    looper.runFor(3)
    looper.run(checkNodesConnected(nodes,
                                   overrideTimeout=10))
    stopNodes(nodes, looper)
    logger.debug("reconnects")
    logger.debug("node order: {}".format(names))
    logger.debug("rwaits: {}".format(rwaits))


def testNodeConnection(allPluginsPath, tdir, looper, nodeReg):
    console = getConsole()
    console.reinit(flushy=True, verbosity=console.Wordage.verbose)
    names = ["Alpha", "Beta"]
    logger.debug(names)
    nrg = {n: nodeReg[n] for n in names}
    A, B = [TestNode(name, nrg, basedirpath=tdir,
                     pluginPaths=allPluginsPath)
            for name in names]
    looper.add(A)
    A.startKeySharing()
    looper.runFor(4)
    logger.debug("wait done")
    looper.add(B)
    B.startKeySharing()
    looper.runFor(4)
    looper.run(checkNodesConnected([A, B]))
    looper.stopall()
    A.start(looper.loop)
    looper.runFor(4)
    B.start(looper.loop)
    looper.run(checkNodesConnected([A, B]))
    stopNodes([A, B], looper)


@pytest.mark.skip(reason="SOV-538. "
                         "Fails due to a bug. Its fixed here "
                         "https://github.com/RaetProtocol/raet/pull/9")
def testNodeConnectionAfterKeysharingRestarted(allPluginsPath, tdir, looper):
    console = getConsole()
    console.reinit(flushy=True, verbosity=console.Wordage.verbose)
    timeout = 60
    names = ["Alpha", "Beta"]
    logger.debug(names)
    nrg = {n: nodeReg[n] for n in names}
    A, B = [TestNode(name, nodeRegistry=nrg, basedirpath=tdir,
                     pluginPaths=allPluginsPath)
            for name in names]
    looper.add(A)
    A.startKeySharing(timeout=timeout)
    looper.runFor(timeout+1)
    logger.debug("done waiting for A's timeout")
    looper.add(B)
    B.startKeySharing(timeout=timeout)
    looper.runFor(timeout+1)
    logger.debug("done waiting for B's timeout")
    A.startKeySharing(timeout=timeout)
    B.startKeySharing(timeout=timeout)
    looper.run(checkNodesConnected([A, B]))
    stopNodes([A, B], looper)


def testNodeRemoveUnknownRemote(allPluginsPath, tdir, looper, nodeReg):
    """
    The nodes Alpha and Beta know about each other so they should connect but
    they should remove remote for C when it tries to connect to them
    """
    names = ["Alpha", "Beta"]
    logger.debug(names)
    nrg = {n: nodeReg[n] for n in names}
    A, B = [TestNode(name, nrg, basedirpath=tdir,
                     pluginPaths=allPluginsPath)
            for name in names]
    for node in (A, B):
        looper.add(node)
        node.startKeySharing()
    looper.run(checkNodesConnected([A, B]))

    C = TestNode("Gamma", {**nrg, **{"Gamma": nodeReg["Gamma"]}},
                 basedirpath=tdir, pluginPaths=allPluginsPath)
    looper.add(C)
    C.startKeySharing(timeout=20)

    def chk():
        assert not C.nodestack.isKeySharing

    looper.run(eventually(chk, retryWait=2, timeout=21))
    stopNodes([C, ], looper)

    def chk():
        assert C.name not in B.nodestack.nameRemotes
        assert C.name not in A.nodestack.nameRemotes

    looper.run(eventually(chk, retryWait=2, timeout=5))
    stopNodes([A, B], looper)
