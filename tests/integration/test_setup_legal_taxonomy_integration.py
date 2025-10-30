import os
import asyncio
import pytest

# Only run when explicitly enabled, as this talks to Neo4j
ENABLE_INTEGRATION = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not ENABLE_INTEGRATION,
    reason="Integration test requires ENABLE_INTEGRATION_TESTS=true and a running Neo4j"
)


@pytest.mark.asyncio
async def test_setup_legal_taxonomy_runs_successfully():
    """Runs the setup script's main() and expects exit code 0 when Neo4j is available."""
    from ingestion.scripts.setup_legal_taxonomy import main

    exit_code = await main()
    assert exit_code == 0
