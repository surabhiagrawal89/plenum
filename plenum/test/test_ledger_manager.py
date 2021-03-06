from plenum.common.ledger_manager import LedgerManager
from plenum.test.testable import Spyable


@Spyable(methods=[LedgerManager.startCatchUpProcess,
                  LedgerManager.catchupCompleted,
                  LedgerManager.processConsistencyProofReq])
class TestLedgerManager(LedgerManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)