"""
Web article content extractor.

Supports general web articles including WeChat (微信公众号) articles.
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from engram.core.types import SourceType
from engram.core.exceptions import ExtractorError
from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class ArticleExtractor(BaseExtractor):
    """
    Web article extractor.

    Uses BeautifulSoup for HTML parsing.
    Supports WeChat articles and general web pages.
    """

    name = "article"
    source_type = SourceType.ARTICLE

    # Domains that this extractor handles
    SUPPORTED_DOMAINS = [
        "mp.weixin.qq.com",  # WeChat articles
        "medium.com",
        "substack.com",
        "zhihu.com",
        "zhuanlan.zhihu.com",
        "juejin.cn",
        "36kr.com",
        "sspai.com",
    ]

    # User agent to avoid blocks
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    async def can_handle(self, url: str) -> bool:
        """Check if URL is a supported article."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if it's a known supported domain
            for supported in self.SUPPORTED_DOMAINS:
                if supported in domain:
                    return True

            # For other URLs, check if it looks like a web page
            if parsed.scheme in ("http", "https"):
                # Exclude common non-article URLs
                excluded_patterns = [
                    r"youtube\.com",
                    r"youtu\.be",
                    r"twitter\.com",
                    r"x\.com",
                    r"facebook\.com",
                    r"instagram\.com",
                    r"tiktok\.com",
                    r"\.pdf$",
                    r"\.jpg$",
                    r"\.png$",
                    r"\.gif$",
                ]
                for pattern in excluded_patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        return False
                return True

        except Exception:
            pass
        return False

    async def extract(self, url: str) -> ExtractionResult:
        """
        Extract article content from URL.

        Args:
            url: Article URL

        Returns:
            ExtractionResult with article content
        """
        logger.info(f"Extracting article from: {url}")

        try:
            # Fetch HTML
            html = await self._fetch_html(url)

            # Parse based on domain
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if "mp.weixin.qq.com" in domain:
                title, content = self._parse_wechat(html)
            else:
                title, content = self._parse_generic(html)

            if not content or len(content.strip()) < 100:
                raise ExtractorError(f"Could not extract meaningful content from: {url}")

            logger.info(f"Extracted article: {len(content)} chars")

            return ExtractionResult(
                title=title or "Untitled Article",
                content=content,
                source_type=SourceType.ARTICLE,
                source_url=url,
                language=self._detect_language(content),
                raw_data={
                    "domain": domain,
                    "content_length": len(content),
                },
            )

        except ExtractorError:
            raise
        except Exception as e:
            logger.error(f"Article extraction error: {e}")
            raise ExtractorError(f"Failed to extract article: {e}") from e

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    raise ExtractorError(f"HTTP {response.status} fetching {url}")
                return await response.text()

    def _parse_wechat(self, html: str) -> tuple[Optional[str], str]:
        """Parse WeChat article HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Get title
        title = None
        title_elem = soup.find("h1", class_="rich_media_title")
        if title_elem:
            title = title_elem.get_text(strip=True)

        # Get content
        content_elem = soup.find("div", class_="rich_media_content")
        if not content_elem:
            content_elem = soup.find("div", id="js_content")

        if content_elem:
            # Remove script and style tags
            for tag in content_elem.find_all(["script", "style"]):
                tag.decompose()

            # Get text with paragraph breaks
            paragraphs = []
            for p in content_elem.find_all(["p", "section", "div"]):
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    paragraphs.append(text)

            content = "\n\n".join(paragraphs)
        else:
            content = ""

        return title, content

    def _parse_generic(self, html: str) -> tuple[Optional[str], str]:
        """Parse generic article HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Get title
        title = None
        for selector in ["h1", "title", ".title", ".article-title"]:
            elem = soup.find(selector)
            if elem:
                title = elem.get_text(strip=True)
                break

        # Get content - try common article containers
        content = ""
        content_selectors = [
            "article",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".content",
            "main",
            ".rich_media_content",
        ]

        for selector in content_selectors:
            if selector.startswith("."):
                elem = soup.find(class_=selector[1:])
            else:
                elem = soup.find(selector)

            if elem:
                # Get all paragraphs
                paragraphs = []
                for p in elem.find_all(["p", "h2", "h3", "li"]):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        paragraphs.append(text)

                if paragraphs:
                    content = "\n\n".join(paragraphs)
                    break

        # Fallback: get all paragraph text
        if not content:
            paragraphs = []
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 30:
                    paragraphs.append(text)
            content = "\n\n".join(paragraphs)

        return title, content

    def _detect_language(self, content: str) -> Optional[str]:
        """Simple language detection."""
        # Check for Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)

        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "zh"
        return "en"
