import importlib.util
import tempfile
import unittest
from pathlib import Path


PARSER_PATH = Path(__file__).parents[1] / ".agents/skills/api-review/scripts/parse_pgy_registry.py"
SPEC = importlib.util.spec_from_file_location("parse_pgy_registry", PARSER_PATH)
PARSER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PARSER)


class ParseRegistryTest(unittest.TestCase):
    def test_parses_name_keyed_registry_row_without_numeric_id(self):
        row = (
            '{Product: "AI SRE", Provider: "safari", Name: "skill:read:list", '
            'NameCN: "技能：列表", Method: "POST", Path: "/safari/skill/list", '
            'Auth: "all", IsDangerous: false, IsAudit: false},\n'
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as fixture:
            fixture.write(row)
            fixture_path = Path(fixture.name)
        try:
            rows = PARSER.parse_file(fixture_path)
        finally:
            fixture_path.unlink()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "skill:read:list")
        self.assertEqual(rows[0]["auth"], "all")
        self.assertEqual(rows[0]["provider"], "safari")

    def test_ignores_non_registry_struct_without_numeric_id(self):
        row = '{Method: "POST", Path: "/test", Auth: "all", Provider: "pgy"},\n'
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as fixture:
            fixture.write(row)
            fixture_path = Path(fixture.name)
        try:
            rows = PARSER.parse_file(fixture_path)
        finally:
            fixture_path.unlink()

        self.assertEqual(rows, [])

    def test_preserves_legacy_registry_row_with_numeric_id(self):
        row = (
            '{ID: 15, Method: "POST", Path: "/team/list", Name: "team:read:list", '
            'Auth: "all", Provider: "pgy"},\n'
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as fixture:
            fixture.write(row)
            fixture_path = Path(fixture.name)
        try:
            rows = PARSER.parse_file(fixture_path)
        finally:
            fixture_path.unlink()

        self.assertEqual(rows[0]["id"], 15)


if __name__ == "__main__":
    unittest.main()
