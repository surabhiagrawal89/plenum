import pytest

from plenum.test.malicious_behaviors_node import makeNodeFaulty, changesRequest

nodeCount = 4
# More faulty nodes(3) then system can tolerate(3)
faultyNodes = 1
whitelist = ['for InvalidSignature',
             'discarding message']
"""
When system has more than f + 1 faulty nodes,
Num of PROPAGATE messages must be less than sufficient (faultyNodes + 1)
"""


# Currently, all the nodes have same malicious
# behavior and should be chose randomly later.

@pytest.fixture(scope="module")
def evilAlpha(nodeSet):
    makeNodeFaulty(nodeSet.Alpha, changesRequest)


def testNumOfPropagateWithOneFault(evilAlpha, propagated1):
    pass
