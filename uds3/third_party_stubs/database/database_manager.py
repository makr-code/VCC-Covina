class DatabaseManager:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_adapter_governance(self):
        return None

    def get_database_manager(self):
        return self
