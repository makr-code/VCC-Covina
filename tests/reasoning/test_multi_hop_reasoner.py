import pytest
from ingestion.reasoning.multi_hop_reasoner import MultiHopReasoner, GraphBackend

class DummyWrapper:
    def __init__(self, graph):
        # graph: dict node -> set(neighbors)
        self.graph = graph
    def run(self, query, params):
        class R:
            def __init__(self, rows):
                self._rows = rows
            def __iter__(self):
                for r in self._rows:
                    yield type('Row', (), {'data': lambda self, r=r: r})()
        # very naive: translate simple queries used by GraphBackend.neighbors and tests
        if "RETURN DISTINCT m.id AS id" in query:
            nid = params["id"]
            neighbors = sorted(list(self.graph.get(nid, [])))
            return R([{ 'id': n } for n in neighbors])
        if "RETURN a.id AS id" in query:
            nid = params["id"]
            # pretend there is an authority linked id -> auth_of_<id>
            return R([{ 'id': f'auth_of_{nid}' }])
        if "shortestPath" in query:
            # return non-empty to indicate a path found
            return R([{ 'p': 'dummy' }])
        return R([])

def test_bfs_find_path_simple():
    g = {
        'A': {'B', 'C'},
        'B': {'D'},
        'C': set(),
        'D': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})
    path = r.find_path('A', 'D', max_hops=3)
    assert path == ['A', 'B', 'D']


def test_bfs_no_path_within_hops():
    g = {
        'A': {'B'},
        'B': {'C'},
        'C': {'D'},
        'D': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})
    assert r.find_path('A', 'D', max_hops=2) is None


def test_authority_for_concept_via_template():
    backend = GraphBackend(DummyWrapper({}))
    r = MultiHopReasoner(backend, templates={
        'authority_for_concept': 'MATCH (c:LegalConcept {id: $id})-[:REFERENCES_AUTHORITY]->(a:Authority) RETURN a.id AS id LIMIT 1'
    })
    assert r.find_authority_for_concept('concept_1') == 'auth_of_concept_1'


def test_explain_relationship_returns_flag():
    g = {
        'A': {'B'},
        'B': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})
    res = r.explain_relationship('A', 'B')
    assert res['path_found'] is True
    assert res['path'] == ['A', 'B']
    assert res['hops'] == 1


def test_dfs_find_path_simple():
    g = {
        'A': {'B', 'C'},
        'B': {'D'},
        'C': set(),
        'D': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})
    path = r.find_path('A', 'D', max_hops=3, strategy='dfs')
    assert path is not None
    assert path[0] == 'A' and path[-1] == 'D'


def test_explain_with_path_details():
    g = {
        'A': {'B'},
        'B': {'C'},
        'C': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})  # No template, use fallback
    res = r.explain_relationship('A', 'C', max_hops=5)
    assert res['path_found'] is True
    assert res['path'] == ['A', 'B', 'C']
    assert res['hops'] == 2
    assert 'A → C via 2 hops' in res['explanation']


def test_explain_no_path():
    g = {
        'A': {'B'},
        'C': set(),
    }
    backend = GraphBackend(DummyWrapper(g))
    r = MultiHopReasoner(backend, templates={})
    res = r.explain_relationship('A', 'C', max_hops=5)
    assert res['path_found'] is False
    assert res['path'] is None
    assert res['hops'] is None
    assert 'No path found' in res['explanation']
