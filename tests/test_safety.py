from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SEMANTIC = load_module(
    "semantic_map_test_target",
    ROOT
    / "plugins"
    / "article-overlap-checker"
    / "skills"
    / "article-overlap-checker"
    / "scripts"
    / "semantic_map.py",
)
COMPETITOR = load_module(
    "competitor_map_test_target",
    ROOT
    / "plugins"
    / "competitor-content-map"
    / "skills"
    / "competitor-content-map"
    / "scripts"
    / "competitor_sitemap_map.py",
)


class UrlSafetyTests(unittest.TestCase):
    def test_article_rejects_non_https_and_private_ip(self) -> None:
        with self.assertRaises(ValueError):
            SEMANTIC.validate_public_https_url("http://example.com/sitemap.xml")
        with self.assertRaises(ValueError):
            SEMANTIC.validate_public_https_url("https://127.0.0.1/sitemap.xml")
        with self.assertRaises(ValueError):
            SEMANTIC.validate_public_https_url("https://169.254.169.254/latest/meta-data")

    def test_competitor_rejects_cross_origin_and_private_ip(self) -> None:
        public_dns = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with mock.patch.object(COMPETITOR.socket, "getaddrinfo", return_value=public_dns):
            origin = COMPETITOR.validate_public_https_url("https://example.com")
            with self.assertRaises(ValueError):
                COMPETITOR.validate_public_https_url("https://other.example/sitemap.xml", origin)
        with self.assertRaises(ValueError):
            COMPETITOR.validate_public_https_url("https://10.0.0.1/sitemap.xml")

    def test_https_connection_uses_the_validated_ip_not_dns_hostname(self) -> None:
        context = mock.Mock()
        sock = mock.Mock()
        connection = SEMANTIC.PinnedHTTPSConnection(
            "rebind.example",
            pinned_ips=("93.184.216.34",),
            expected_hostname="rebind.example",
            context=context,
        )
        with mock.patch.object(connection, "_create_connection", return_value=sock) as create:
            connection.connect()
        create.assert_called_once_with(
            ("93.184.216.34", 443),
            connection.timeout,
            connection.source_address,
        )
        context.wrap_socket.assert_called_once_with(sock, server_hostname="rebind.example")


class PartialDataTests(unittest.TestCase):
    def test_article_sitemap_index_fails_closed(self) -> None:
        xml = "<sitemapindex>" + "".join(
            f"<sitemap><loc>https://example.com/sitemap?id={index}</loc></sitemap>"
            for index in range(2)
        ) + "</sitemapindex>"
        public_dns = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with (
            mock.patch.object(SEMANTIC.socket, "getaddrinfo", return_value=public_dns),
            mock.patch.object(SEMANTIC, "fetch", return_value=xml) as fetch_mock,
        ):
            pages, incomplete = SEMANTIC.load_from_sitemap("https://example.com/sitemap.xml")
        self.assertEqual([], pages)
        self.assertTrue(incomplete)
        fetch_mock.assert_called_once()

    def test_article_partial_source_returns_exit_three_without_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.md"
            argv = [
                "semantic_map.py",
                "--sitemap",
                "https://example.com/sitemap.xml",
                "--out",
                str(report),
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(SEMANTIC, "load_from_sitemap", return_value=([("a", "x" * 300)], True)),
            ):
                code = SEMANTIC.main()
            self.assertEqual(3, code)
            self.assertFalse(report.exists())

    def test_competitor_partial_source_writes_diagnostic_and_returns_three(self) -> None:
        good = COMPETITOR.SiteData(
            domain="https://good.example",
            urls=[("https://good.example/post", "2026-08-02")],
            sitemaps_used=["https://good.example/sitemap.xml"],
        )
        missing = COMPETITOR.SiteData(domain="https://missing.example", errors=["抓不到 sitemap"])
        with tempfile.TemporaryDirectory() as temp_dir:
            argv = [
                "competitor_sitemap_map.py",
                "--vs",
                "good.example",
                "missing.example",
                "--out",
                temp_dir,
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(COMPETITOR, "crawl_domain", side_effect=[good, missing]),
            ):
                code = COMPETITOR.main()
            self.assertEqual(3, code)
            self.assertEqual(1, len(list(Path(temp_dir).glob("diagnostic-*.md"))))
            self.assertEqual(1, len(list(Path(temp_dir).glob("diagnostic-*.json"))))

    def test_competitor_child_sitemap_failure_marks_site_incomplete(self) -> None:
        index = b"""<sitemapindex>
            <sitemap><loc>https://example.com/good</loc></sitemap>
            <sitemap><loc>https://example.com/missing</loc></sitemap>
        </sitemapindex>"""
        child = b"""<urlset>
            <url><loc>https://example.com/post</loc></url>
        </urlset>"""
        responses = {
            "https://example.com/sitemap.xml": index,
            "https://example.com/robots.txt": None,
            "https://example.com/good": child,
            "https://example.com/missing": None,
        }
        with (
            mock.patch.object(COMPETITOR, "validate_public_https_url", return_value=("https", "example.com", 443)),
            mock.patch.object(COMPETITOR, "fetch", side_effect=lambda url, origin: responses.get(url)),
        ):
            site = COMPETITOR.crawl_domain("example.com", False)
        self.assertEqual(1, len(site.urls))
        self.assertTrue(site.incomplete)

    def test_competitor_cross_origin_robots_sitemap_marks_site_incomplete(self) -> None:
        sitemap = b"""<urlset>
            <url><loc>https://example.com/post</loc></url>
        </urlset>"""
        robots = b"Sitemap: https://cdn.example.net/extra-sitemap.xml\n"
        responses = {
            "https://example.com/sitemap.xml": sitemap,
            "https://example.com/robots.txt": robots,
        }
        with (
            mock.patch.object(COMPETITOR, "validate_public_https_url", return_value=("https", "example.com", 443)),
            mock.patch.object(COMPETITOR, "fetch", side_effect=lambda url, origin: responses.get(url)),
        ):
            site = COMPETITOR.crawl_domain("example.com", False)
        self.assertEqual(1, len(site.urls))
        self.assertTrue(site.incomplete)
        self.assertTrue(any("忽略跨來源" in message for message in site.errors))


class ArgumentContractTests(unittest.TestCase):
    def test_competitor_requires_at_least_one_rival(self) -> None:
        with mock.patch.object(sys, "argv", ["competitor_sitemap_map.py", "--you", "example.com"]):
            self.assertEqual(2, COMPETITOR.main())

    def test_competitor_ai_modes_are_mutually_exclusive(self) -> None:
        argv = ["competitor_sitemap_map.py", "--vs", "example.com", "--cc", "--ai"]
        with mock.patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as raised:
            COMPETITOR.main()
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
