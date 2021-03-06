import unittest
from maggma.schema import StandardSchema
from monty.json import MSONable

class SchemaTests(unittest.TestCase):

    def test_standardschema(self):

        class LatticeMock(MSONable):
            def __init__(self, a):
                self.a = a

        class SampleSchema(StandardSchema):
            @property
            def schema(self):
                return {
                    "type": "object",
                    "properties":
                        {
                            "task_id": {"type": "string"},
                            "successful": {"type": "boolean"}
                        },
                    "required": ["task_id", "successful"]
                }
            @property
            def msonable_keypaths(self):
                return {"lattice": LatticeMock}

        schema = SampleSchema()

        lattice = LatticeMock(5)

        valid_doc = {
            'task_id': 'mp-test',
            'successful': True,
            'lattice': lattice.as_dict()
        }

        invalid_doc_msonable = {
            'task_id': 'mp-test',
            'successful': True,
            'lattice': ['I am not a lattice!']
        }

        invalid_doc_missing_key = {
            'task_id': 'mp-test',
            'lattice': lattice.as_dict()
        }

        invalid_doc_wrong_type = {
            'task_id': 'mp-test',
            'successful': 'true',
            'lattice': lattice.as_dict()
        }

        self.assertTrue(schema.is_valid(valid_doc))
        self.assertFalse(schema.is_valid(invalid_doc_msonable))
        self.assertFalse(schema.is_valid(invalid_doc_missing_key))
        self.assertFalse(schema.is_valid(invalid_doc_wrong_type))