from enum import Enum

class RelationType(Enum):
    PART_OF = 'PART_OF'
    UDS3_LEGAL_REFERENCE = 'UDS3_LEGAL_REFERENCE'

class GraphLevel(Enum):
    DOCUMENT = 'document'

class RelationDefinition:
    def __init__(self, name:str, attrs:dict=None):
        self.name = name
        self.attrs = attrs or {}

class VERITASRelationAlmanach:
    def get_definition(self, name):
        return RelationDefinition(name)
