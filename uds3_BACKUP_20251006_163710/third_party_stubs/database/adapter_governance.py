class AdapterGovernanceError(Exception):
    pass

class AdapterGovernance:
    def ensure_operation_allowed(self, backend_key, operation):
        return True

    def enforce_payload(self, backend_key, operation, payload):
        return payload
