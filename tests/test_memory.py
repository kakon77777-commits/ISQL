import tempfile
import unittest
from pathlib import Path

from isql_core.memory import encode_text_memory
from isql_core.store import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_memory_has_r0_to_r4(self):
        rec = encode_text_memory("Alpha beta. Alpha gamma.")
        self.assertEqual(tuple(rec.layers), ("R0", "R1", "R2", "R3", "R4"))

    def test_address_is_separate_from_memory_codes(self):
        rec = encode_text_memory("same source")
        self.assertEqual(rec.address.domain, "ADDR")
        for layer in rec.layers.values():
            self.assertEqual(layer.code.domain, "MEM")
            self.assertNotEqual(layer.code.to_wire(), rec.address.to_wire())

    def test_same_source_same_memory_codes(self):
        a = encode_text_memory("Alpha beta. Alpha gamma.")
        b = encode_text_memory("Alpha beta. Alpha gamma.")
        self.assertEqual(
            [x.code for x in a.layers.values()],
            [x.code for x in b.layers.values()],
        )

    def test_r0_is_locator_only(self):
        rec = encode_text_memory("secret body text")
        data = rec.layers["R0"].data
        self.assertIn("address", data)
        self.assertIn("byte_length", data)
        self.assertNotIn("text", data)
        self.assertNotIn("exact_source", data)

    def test_r1_is_smaller_than_exact_source(self):
        text = "alpha beta gamma " * 100
        rec = encode_text_memory(text)
        self.assertLess(len(str(rec.layers["R1"].data)), len(text))

    def test_r4_can_recover_exact_text(self):
        text = "line 1\n第二行\n"
        rec = encode_text_memory(text)
        self.assertEqual(rec.layers["R4"].data["exact_source"], text)

    def test_metadata_changes_memory_representation_not_address(self):
        a = encode_text_memory("same", metadata={"topic": "A"})
        b = encode_text_memory("same", metadata={"topic": "B"})
        self.assertEqual(a.address, b.address)
        self.assertNotEqual(a.layers["R3"].code, b.layers["R3"].code)

    def test_store_round_trip_by_address(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td))
            rec = encode_text_memory("persistent memory", metadata={"k": 1})
            store.put(rec)
            loaded = store.get(rec.address)
            self.assertEqual(loaded.to_dict(), rec.to_dict())


if __name__ == "__main__":
    unittest.main()
