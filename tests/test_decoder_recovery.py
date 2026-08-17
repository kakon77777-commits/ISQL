import tempfile
import unittest
from pathlib import Path

from isql_core.decoder import CallableAIDecoder, DeterministicMemoryDecoder
from isql_core.memory import encode_text_memory
from isql_core.recoverability import evaluate_recovery, token_jaccard
from isql_core.store import MemoryStore


class DecoderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name))
        self.text = "Alpha beta gamma. Alpha delta."
        self.record = encode_text_memory(self.text)
        self.store.put(self.record)
        self.decoder = DeterministicMemoryDecoder(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_r4_exact_recovery(self):
        result = self.decoder.decode(self.record.layers["R4"].code)
        self.assertTrue(result.exact)
        self.assertEqual(result.recovered_text, self.text)

    def test_r0_has_no_reconstructed_text(self):
        result = self.decoder.decode(self.record.layers["R0"].code)
        self.assertFalse(result.exact)
        self.assertIsNone(result.recovered_text)

    def test_r3_recovers_normalized_text(self):
        result = self.decoder.decode(self.record.layers["R3"].code)
        self.assertEqual(result.recovered_text, self.text)
        self.assertFalse(result.exact)

    def test_recovery_report_separates_exact_and_semantic(self):
        r1 = self.decoder.decode(self.record.layers["R1"].code)
        report = evaluate_recovery(self.text, r1)
        self.assertFalse(report.exact)
        self.assertGreater(report.semantic_score, 0.0)
        self.assertLessEqual(report.semantic_score, 1.0)

    def test_token_jaccard(self):
        self.assertEqual(token_jaccard("a b", "a b"), 1.0)
        self.assertEqual(token_jaccard("a", "b"), 0.0)

    def test_callable_ai_decoder_records_decoder_identity(self):
        ai = CallableAIDecoder(
            base=self.decoder,
            decoder_id="demo-ai",
            decoder_contract="semantic-recovery/v1",
            fn=lambda base, context: (base.recovered_text or "") + " expanded",
        )
        result = ai.decode(self.record.layers["R1"].code, context={"hint": "x"})
        self.assertEqual(result.decoder_id, "demo-ai")
        self.assertEqual(result.decoder_contract, "semantic-recovery/v1")
        self.assertTrue(result.recovered_text.endswith(" expanded"))
        self.assertFalse(result.exact)


if __name__ == "__main__":
    unittest.main()
