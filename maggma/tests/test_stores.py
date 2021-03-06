import os
import glob
import unittest
import numpy as np
import mongomock.collection
import pymongo.collection
import numpy.testing.utils as nptu
from maggma.stores import *

module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
db_dir = os.path.abspath(os.path.join(
    module_dir, "..", "..", "test_files", "settings_files"))
test_dir = os.path.abspath(os.path.join(
    module_dir, "..", "..", "test_files", "test_set"))


class TestMongoStore(unittest.TestCase):

    def setUp(self):
        self.mongostore = MongoStore("maggma_test", "test")
        self.mongostore.connect()

    def test_connect(self):
        mongostore = MongoStore("maggma_test", "test")
        self.assertEqual(mongostore.collection, None)
        mongostore.connect()
        self.assertIsInstance(mongostore.collection,
                              pymongo.collection.Collection)

    def test_query(self):
        self.mongostore.collection.insert({"a": 1, "b": 2, "c": 3})
        self.assertEqual(self.mongostore.query_one(properties=["a"])["a"], 1)
        self.assertEqual(self.mongostore.query_one(properties=["a"])['a'], 1)
        self.assertEqual(self.mongostore.query_one(properties=["b"])['b'], 2)
        self.assertEqual(self.mongostore.query_one(properties=["c"])['c'], 3)

    def test_distinct(self):
        self.mongostore.collection.insert({"a": 1, "b": 2, "c": 3})
        self.mongostore.collection.insert({"a": 4, "d": 5, "e": 6})
        self.assertEqual(self.mongostore.distinct("a"), [1, 4])

        # Test list distinct functionality
        self.mongostore.collection.insert({"a": 4, "d": 6, "e": 7})
        self.mongostore.collection.insert({"a": 4, "d": 6})
        ad_distinct = self.mongostore.distinct(["a", "d"])
        self.assertTrue(len(ad_distinct), 3)
        self.assertTrue({"a": 4, "d": 6} in ad_distinct)
        self.assertTrue({"a": 1} in ad_distinct)
        self.assertEqual(len(self.mongostore.distinct(["d", "e"], {"a": 4})), 3)
        all_exist = self.mongostore.distinct(["a", "b"], all_exist=True)
        self.assertEqual(len(all_exist), 1)
        all_exist2 = self.mongostore.distinct(
            ["a", "e"], all_exist=True, criteria={"d": 6})
        self.assertEqual(len(all_exist2), 1)

    def test_update(self):
        self.mongostore.update([{"e": 6, "d": 4}], key="e")
        self.assertEqual(self.mongostore.query(
            criteria={"d": {"$exists": 1}}, properties=["d"])[0]["d"], 4)

        self.mongostore.update([{"e": 7, "d": 8, "f": 9}], key=["d", "f"])
        self.assertEqual(self.mongostore.query_one(
            criteria={"d": 8, "f": 9}, properties=["e"])["e"], 7)
        self.mongostore.update([{"e": 11, "d": 8, "f": 9}], key=["d", "f"])
        self.assertEqual(self.mongostore.query_one(
            criteria={"d": 8, "f": 9}, properties=["e"])["e"], 11)

    def test_groupby(self):
        self.mongostore.collection.drop()
        self.mongostore.update([{"e": 7, "d": 9, "f": 9},
                                {"e": 7, "d": 9, "f": 10},
                                {"e": 8, "d": 9, "f": 11},
                                {"e": 9, "d": 10, "f": 12}], key="f")
        data = list(self.mongostore.groupby("d"))
        self.assertEqual(len(data), 2)
        grouped_by_9 = [g['docs'] for g in data if g['_id']['d'] == 9][0]
        self.assertEqual(len(grouped_by_9), 3)
        grouped_by_10 = [g['docs'] for g in data if g['_id']['d'] == 10][0]
        self.assertEqual(len(grouped_by_10), 1)

        data = list(self.mongostore.groupby(["e", "d"]))
        self.assertEqual(len(data), 3)

    def test_from_db_file(self):
        ms = MongoStore.from_db_file(os.path.join(db_dir, "db.json"))
        self.assertEqual(ms.collection_name,"tmp")

    def tearDown(self):
        if self.mongostore.collection:
            self.mongostore.collection.drop()


class TestMemoryStore(unittest.TestCase):

    def setUp(self):
        self.memstore = MemoryStore()

    def test(self):
        self.assertEqual(self.memstore.collection, None)
        self.memstore.connect()
        self.assertIsInstance(self.memstore.collection,
                              mongomock.collection.Collection)

    def test_groupby(self):
        self.assertRaises( NotImplementedError, self.memstore.groupby, "a")


class TestJsonStore(unittest.TestCase):

    def test(self):
        files = []
        for f in ["a.json", "b.json"]:
            files.append(os.path.join(test_dir, f))

        jsonstore = JSONStore(files)
        jsonstore.connect()
        self.assertEqual(len(list(jsonstore.query())), 20)

        jsonstore = JSONStore(os.path.join(test_dir, "c.json.gz"))
        jsonstore.connect()
        self.assertEqual(len(list(jsonstore.query())), 20)


class TestGridFSStore(unittest.TestCase):

    def setUp(self):
        self.gStore = GridFSStore("maggma_test", "test", key="task_id")
        self.gStore.connect()

    def test_update(self):
        data1 = np.random.rand(256)
        self.gStore.update([{"task_id": "mp-1", "data": data1}])
        self.assertTrue(self.gStore._files_collection.find_one({"task_id": "mp-1"}))

    def test_query(self):
        data1 = np.random.rand(256)
        data2 = np.random.rand(256)
        self.gStore.update([{"task_id": "mp-1", "data": data1}])
        self.gStore.update([{"task_id": "mp-2", "data": data2}])

        doc = self.gStore.query_one(criteria={"task_id": "mp-1"})
        nptu.assert_almost_equal(doc["data"], data1, 7)

        doc = self.gStore.query_one(criteria={"task_id": "mp-2"})
        nptu.assert_almost_equal(doc["data"], data2, 7)

        self.assertEqual(self.gStore.query_one(criteria={"task_id": "mp-3"}), None)

    def test_distinct(self):
        self.gStore.update([{"task_id": "mp-1", "data": "Something"}])
        self.gStore.update([{"task_id": "mp-2", "data": "Something"}])
        self.gStore.update([{"task_id": "mp-3", "data": "Something"}])
        self.gStore.update([{"task_id": "mp-4", "material_id": "mvc-1", "data": "Something"}])
        self.gStore.update([{"task_id": "mp-5", "material_id": "mvc-1", "data": "Something"}])

    def tearDown(self):
        if self.gStore.collection:
            self.gStore._files_collection.drop()
            self.gStore._chunks_collection.drop()


if __name__ == "__main__":
    unittest.main()
