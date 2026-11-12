import unittest

from src.data_collection.fetch_product_updates import (
    classify_affected_areas,
    parse_notion_releases,
)


class ParseNotionReleasesTests(unittest.TestCase):
    def test_parse_notion_releases_extracts_date_title_summary_and_version(self):
        html = """
        <html><body>
          <h1>What's New</h1>
          <p>July 1, 2026 3.6</p>
          <a href="/releases/notion-3-6">Notion 3.6: External Agents, HTML blocks, and more</a>
          <p>Your agents can now read and write Excel and PowerPoint files.</p>
          <p>AI Meeting Notes now include speaker labels.</p>
          <p>May 26, 2026</p>
          <a href="/releases/merge-cells">Merge cells in simple tables</a>
          <p>Finally! Merge cells in simple tables.</p>
        </body></html>
        """

        releases = parse_notion_releases(html, "https://www.notion.com/releases")

        self.assertEqual(len(releases), 2)
        self.assertEqual(releases[0]["release_date"], "2026-07-01")
        self.assertEqual(releases[0]["release_version"], "3.6")
        self.assertEqual(
            releases[0]["release_title"],
            "Notion 3.6: External Agents, HTML blocks, and more",
        )
        self.assertIn("speaker labels", releases[0]["release_summary"])
        self.assertEqual(
            releases[0]["source_url"],
            "https://www.notion.com/releases/notion-3-6",
        )
        self.assertEqual(releases[1]["release_date"], "2026-05-26")
        self.assertEqual(releases[1]["release_version"], "")


    def test_parse_notion_releases_handles_separate_version_text(self):
        html = """
        <html><body>
          <p>July 1, 2026</p>
          <p>3.6</p>
          <a href="/releases/2026-07-01">Notion 3.6: External Agents, HTML blocks, and more</a>
          <p>Uh-oh! It looks like your ad blocker is preventing the video from playing.</p>
          <p>Your agents can now read and write Excel files.</p>
        </body></html>
        """

        releases = parse_notion_releases(html, "https://www.notion.com/releases")

        self.assertEqual(releases[0]["release_version"], "3.6")
        self.assertEqual(
            releases[0]["release_title"],
            "Notion 3.6: External Agents, HTML blocks, and more",
        )
        self.assertNotIn("ad blocker", releases[0]["release_summary"])


    def test_parse_notion_releases_stops_before_footer_navigation(self):
        html = """
        <html><body>
          <p>April 27, 2026</p>
          <a href="/releases/2026-04-27">Rollups now as currency, percent, and more</a>
          <p>Rollups now support number formatting.</p>
          <a href="/releases/page/2">Next page</a>
          <p>Contact sales</p>
        </body></html>
        """

        releases = parse_notion_releases(html, "https://www.notion.com/releases")

        self.assertIn("number formatting", releases[0]["release_summary"])
        self.assertNotIn("Contact sales", releases[0]["release_summary"])


class ClassifyAffectedAreasTests(unittest.TestCase):
    def test_classify_affected_areas_uses_release_keywords(self):
        areas, keywords = classify_affected_areas(
            "Android performance fixes",
            "Fixed slow loading and crashes on mobile.",
        )

        self.assertIn("mobile_app", areas)
        self.assertIn("performance", areas)
        self.assertIn("android", keywords)
        self.assertIn("crash", keywords)

    def test_classify_affected_areas_falls_back_to_other(self):
        areas, keywords = classify_affected_areas("Small polish", "A few more updates.")

        self.assertEqual(areas, ["other"])
        self.assertEqual(keywords, [])


if __name__ == "__main__":
    unittest.main()
