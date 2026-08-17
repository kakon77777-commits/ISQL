import unittest
from pathlib import Path

from isql_core.code import parse_code
from isql_core.errors import ISQLValidationError, ISQLExecutionError
from isql_core.registry import DomainRegistry


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = DomainRegistry.load_default()

    def test_bootstrap_domains_exact(self):
        self.assertEqual(
            set(self.registry.domain_ids()),
            {"ADDR", "MEM", "SEM", "STATE", "EXEC", "RESERVED"},
        )

    def test_memory_allows_all_resolution_levels(self):
        domain = self.registry.get("MEM")
        self.assertEqual(domain.resolutions, ("R0", "R1", "R2", "R3", "R4"))

    def test_unknown_domain_fails_closed(self):
        code = parse_code("ISQL1:UNKNOWN:R0:X123")
        with self.assertRaises(ISQLValidationError):
            self.registry.validate_code(code)

    def test_reserved_domain_is_not_executable(self):
        code = parse_code("ISQL1:RESERVED:R0:X123")
        self.registry.validate_code(code)
        with self.assertRaises(ISQLExecutionError):
            self.registry.require_executable(code.domain)

    def test_address_only_allows_r0(self):
        code = parse_code("ISQL1:ADDR:R2:H123")
        with self.assertRaises(ISQLValidationError):
            self.registry.validate_code(code)


if __name__ == "__main__":
    unittest.main()
