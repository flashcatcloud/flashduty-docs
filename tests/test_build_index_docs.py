import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts/build_index_docs.py"
SPEC = importlib.util.spec_from_file_location("build_index_docs", SCRIPT_PATH)
BUILD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD)


def build_page(rel_path, text):
    """Write text at rel_path under a temp repo root and build its documents."""
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / rel_path
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(root)
        try:
            return list(BUILD.build(rel_path))
        finally:
            os.chdir(cwd)


class BuildIndexDocsTest(unittest.TestCase):
    def test_long_chinese_page_is_fully_indexed_within_byte_limit(self):
        paragraphs = [f"第{i}段：分派策略按顺序匹配，命中后通知值班人员。" * 12 for i in range(60)]
        text = "---\ntitle: 分派策略\n---\n\n## 配置要素\n\n" + "\n\n".join(paragraphs)
        docs = build_page("zh/on-call/escalation.mdx", text)

        self.assertGreater(len(docs), 1)
        for doc in docs:
            self.assertLessEqual(len(doc["content"].encode("utf-8")), BUILD.MAX_CHUNK_BYTES)
            self.assertNotIn("�", doc["content"])
        joined = "\n".join(doc["content"] for doc in docs)
        for paragraph in paragraphs:
            self.assertIn(paragraph, joined)

    def test_single_oversized_line_splits_on_character_boundaries(self):
        line = "告警" * 3000
        docs = build_page("zh/a.mdx", "---\ntitle: T\n---\n\n" + line)
        for doc in docs:
            self.assertLessEqual(len(doc["content"].encode("utf-8")), BUILD.MAX_CHUNK_BYTES)
        body = "".join(doc["content"].split("\n\n", 1)[1] for doc in docs)
        self.assertEqual(body, line)

    def test_tags_are_stripped_but_titles_placeholders_and_code_survive(self):
        text = (
            "---\ntitle: Web SDK\n---\n\n"
            "<Steps>\n<Step title=\"Create the app\">\nReplace <YOUR_APP_KEY> first.\n</Step>\n</Steps>\n\n"
            "<Note>Keep it secret.</Note>\n\n"
            "```html\n<script src=\"https://static.flashcat.cloud/browser-sdk/v0/flashcat-rum.js\"></script>\n```\n"
        )
        content = build_page("en/rum/web.mdx", text)[0]["content"]

        self.assertIn("Create the app", content)
        self.assertIn("<YOUR_APP_KEY>", content)
        self.assertIn('<script src="https://static.flashcat.cloud/browser-sdk/v0/flashcat-rum.js"></script>', content)
        self.assertIn("Keep it secret.", content)
        self.assertNotIn("<Note>", content)
        self.assertNotIn("<Step", content)

    def test_chunk_breadcrumb_names_where_it_starts(self):
        filler = "x" * 1400
        text = "---\ntitle: Routing\n---\n\n## Rules\n\n### Conditions\n\n" + "\n\n".join([filler] * 4)
        docs = build_page("en/on-call/routing.mdx", text)

        self.assertTrue(docs[0]["content"].startswith("Routing > Rules > Conditions\n\n"))
        self.assertTrue(docs[-1]["content"].startswith("Routing > Rules > Conditions\n\n"))

    def test_ids_locale_and_urls(self):
        docs = build_page("zh/on-call/a.mdx", "---\ntitle: A\n---\n\n" + "\n\n".join(["y" * 2000] * 3))
        pid = BUILD.page_id("zh/on-call/a.mdx")
        self.assertEqual([d["id"] for d in docs], [f"{pid}-{i:03d}" for i in range(len(docs))])
        self.assertEqual({d["locale"] for d in docs}, {"zh-CN"})
        self.assertEqual(docs[0]["url"], BUILD.BASE_URL + "/zh/on-call/a")

        relative = build_page("zh/openapi.mdx", "---\ntitle: API\ndescription: Open API\nurl: /zh/openapi/introduction\n---\n")
        self.assertEqual(relative[0]["url"], BUILD.BASE_URL + "/zh/openapi/introduction")

    def test_link_only_page_is_indexed_by_its_description(self):
        text = '---\ntitle: Terraform Provider\ndescription: "Manage Flashduty resources as code"\nurl: https://registry.terraform.io/providers/flashcatcloud/flashduty\n---\n'
        docs = build_page("en/developer/terraform.mdx", text)

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["content"], "Terraform Provider\n\nManage Flashduty resources as code")
        self.assertEqual(docs[0]["url"], "https://registry.terraform.io/providers/flashcatcloud/flashduty")


if __name__ == "__main__":
    unittest.main()
