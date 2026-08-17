import unittest

from isql_core.errors import ISQLValidationError
from isql_core.hierarchical import HierarchicalRegistry, tokenize_registry_text


class HierarchicalRegistryTests(unittest.TestCase):
    def test_tokenizer_reconstructs_english_exactly(self):
        text = "Semantic memory, exact recovery."
        tokens = tokenize_registry_text(text)
        self.assertEqual("".join(tokens), text)
        self.assertIn("Semantic", tokens)
        self.assertIn(" ", tokens)

    def test_tokenizer_reconstructs_traditional_chinese_and_whitespace_exactly(self):
        text = "語義記憶  與定址：不可混同。\n下一行"
        tokens = tokenize_registry_text(text)
        self.assertEqual("".join(tokens).encode("utf-8"), text.encode("utf-8"))
        self.assertIn("語", tokens)
        self.assertIn("  ", tokens)
        self.assertIn("\n", tokens)

    def test_lexeme_ids_are_stable_and_program_round_trips(self):
        reg = HierarchicalRegistry.empty()
        p1 = reg.encode_value("semantic memory")
        p2 = reg.encode_value("semantic recovery")
        self.assertEqual(reg.decode_value(p1), "semantic memory")
        self.assertEqual(reg.decode_value(p2), "semantic recovery")
        semantic_id = reg.lexemes.index("semantic") + 1
        self.assertEqual(p1[0], semantic_id)
        self.assertEqual(p2[0], semantic_id)

    def test_invalid_lexeme_id_fails_closed(self):
        reg = HierarchicalRegistry.empty()
        with self.assertRaises(ISQLValidationError):
            reg.decode_value((1,))


if __name__ == "__main__":
    unittest.main()
