"""
Smoke test: ensure process gap endpoints are registered in router.
This test does not hit databases; it only inspects route paths.
"""
from backend.queries.process_queries import router


def test_gap_routes_present():
    paths = {r.path for r in router.routes}
    # Router has prefix "/processes"; routes include that in .path
    expected = {
        "/processes/gaps/missing-roles",
        "/processes/gaps/dead-ends",
        "/processes/gaps/unconnected-steps",
        "/processes/gaps/missing-controls",
        "/processes/gaps/missing-legal-refs",
        "/processes/gaps/cycles",
        "/processes/gaps/temporal-inconsistencies",
    }
    # All expected paths should be present
    missing = expected - paths
    assert not missing, f"Missing gap routes: {missing}"
