import time
import logging
from typing import Optional

from database.database_manager import DatabaseManager
from database.saga_orchestrator import SagaOrchestrator
from database import config

logger = logging.getLogger(__name__)


class SagaRecoveryWorker:
    def __init__(self, manager: Optional[DatabaseManager] = None):
        self.manager = manager or DatabaseManager(config.get_database_backend_dict())
        self.orch = SagaOrchestrator(manager=self.manager)

    def _list_open_sagas(self):
        rel = self.manager.get_relational_backend()
        if not rel:
            return []
        rows = rel.execute_query("SELECT saga_id, status FROM uds3_sagas WHERE status NOT IN ('completed','compensated','aborted')")
        return [r['saga_id'] for r in rows]

    def run_once(self, max_retries: int = 3):
        sagas = self._list_open_sagas()
        results = {}
        for saga_id in sagas:
            attempt = 0
            while attempt < max_retries:
                try:
                    res = self.orch.resume_saga(saga_id)
                    results[saga_id] = res
                    break
                except Exception as exc:
                    attempt += 1
                    sleep = 0.1 * (2 ** attempt)
                    logger.debug('Resume for %s failed attempt %d: %s', saga_id, attempt, exc)
                    time.sleep(sleep)
                    continue
        return results


def main():
    logging.basicConfig(level=logging.INFO)
    worker = SagaRecoveryWorker()
    res = worker.run_once()
    logger.info('Recovery run results: %s', res)


if __name__ == '__main__':
    main()
