"""CrawlabilityScorer -- evaluates whether AI crawlers can access and read page content.

Implements 12 criteria (C1-C12):
- C1-C8: AI bot access via robots.txt (binary)
- C9: Server-side rendering detection via Playwright JS vs no-JS comparison (gradient)
- C10: Response time / TTFB measurement (gradient)
- C11: HTTP status code check with AI bot User-Agent (binary)
- C12: Resource blockage detection in robots.txt (gradient)

Crawlability is 25% of the Optimization Score and is the #1 technical factor --
"if AI can't read your content, nothing else matters" (Otterly.ai).
"""

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger

from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult

# AI bots to check: (criterion_id, bot_display_name, ai_bot_access_field_or_None, user_agent_string)
# field_or_None: if a string, read from crawl_data["ai_bot_access"][field]; if None, check robots.txt directly
AI_BOT_CRITERIA: list[tuple[str, str, str | None, str]] = [
    ("C1", "GPTBot", "gptbot", "GPTBot"),
    ("C2", "ClaudeBot", "claudebot", "ClaudeBot"),
    ("C3", "PerplexityBot", "perplexitybot", "PerplexityBot"),
    ("C4", "OAI-SearchBot", None, "OAI-SearchBot"),
    ("C5", "Claude-SearchBot", "claude_searchbot", "Claude-SearchBot"),
    ("C6", "Bingbot", None, "Bingbot"),
    ("C7", "CCBot", "ccbot", "CCBot"),
    ("C8", "Google-Extended", "google_extended", "Google-Extended"),
]

# Bot purpose descriptions for human summaries
BOT_PURPOSE: dict[str, str] = {
    "GPTBot": "ChatGPT can access and cite your content",
    "ClaudeBot": "Claude can access and cite your content",
    "PerplexityBot": "Perplexity can access and cite your content",
    "OAI-SearchBot": "OpenAI SearchBot can index your content",
    "Claude-SearchBot": "Claude Search can find your content",
    "Bingbot": "Bing (used by Copilot) can access your content",
    "CCBot": "Common Crawl (training data) can access your content",
    "Google-Extended": "Google AI features (Bard/Gemini) can use your content",
}


class CrawlabilityScorer(BaseScorer):
    """Scores pages on 12 crawlability criteria for AI readiness.

    Checks robots.txt access for 8 AI bots, SSR quality via Playwright,
    TTFB, HTTP status code, and resource blockage.

    Attributes:
        _robots_cache: Per-domain cache of (robots_txt_content, RobotFileParser) tuples.
        _browser: Playwright browser instance for SSR detection, lazily initialized.
    """

    def __init__(self):
        self._robots_cache: dict[str, tuple[str, RobotFileParser]] = {}
        self._browser = None
        self._playwright = None

    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Score a single page against all 12 crawlability criteria.

        Args:
            page_data: Dict from CrawlResult.model_dump() with keys:
                url, domain, main_content, ai_bot_access, etc.

        Returns:
            List of 12 ScoringCriterionResult instances (C1-C12).
        """
        url = page_data.get("url", "")
        crawl_data = page_data
        no_js_content = page_data.get("main_content", "")

        results: list[ScoringCriterionResult] = []

        # C1-C8: AI bot access checks
        for criterion_id, bot_name, field, user_agent in AI_BOT_CRITERIA:
            if field is not None:
                result = self._check_bot_access(
                    bot_name=bot_name,
                    bot_field=field,
                    criterion_id=criterion_id,
                    crawl_data=crawl_data,
                )
            else:
                result = await self._check_robots_txt_direct(
                    url=url,
                    user_agent=user_agent,
                    criterion_id=criterion_id,
                    bot_name=bot_name,
                )
            results.append(result)

        # C9: SSR detection
        results.append(await self._check_ssr(url, no_js_content))

        # C10: TTFB
        results.append(await self._check_ttfb(url))

        # C11: HTTP status code
        results.append(await self._check_status_code(url))

        # C12: Resource blockage
        results.append(await self._check_resource_blockage(url, crawl_data))

        return results

    def _check_bot_access(
        self,
        bot_name: str,
        bot_field: str,
        criterion_id: str,
        crawl_data: dict,
    ) -> ScoringCriterionResult:
        """Check AI bot access from pre-crawled ai_bot_access data.

        Args:
            bot_name: Display name of the bot (e.g., "GPTBot").
            bot_field: Key in ai_bot_access dict (e.g., "gptbot").
            criterion_id: Criterion ID (e.g., "C1").
            crawl_data: Crawl result dict containing ai_bot_access.

        Returns:
            ScoringCriterionResult with score 100 (allowed/no directive) or 0 (blocked).
        """
        ai_bot_access = crawl_data.get("ai_bot_access", {})
        access_value = ai_bot_access.get(bot_field)

        purpose = BOT_PURPOSE.get(bot_name, "can access your content")

        if access_value is True:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=f"{bot_name} access",
                score=100,
                is_binary=True,
                human_summary=f"{bot_name}: ALLOWED -- {purpose}",
                technical_detail=f"robots.txt explicitly allows {bot_name}",
                evidence={"bot": bot_name, "status": "allowed", "directive": "Allow"},
            )
        elif access_value is False:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=f"{bot_name} access",
                score=0,
                is_binary=True,
                human_summary=f"{bot_name}: BLOCKED via robots.txt -- {purpose.replace('can', 'cannot')}",
                technical_detail=f"robots.txt contains Disallow directive for {bot_name}",
                evidence={"bot": bot_name, "status": "blocked", "directive": "Disallow"},
            )
        else:
            # None = no directive found, assumed allowed
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=f"{bot_name} access",
                score=100,
                is_binary=True,
                human_summary=f"{bot_name}: ALLOWED (no specific directive) -- {purpose}",
                technical_detail=f"No Disallow directive for {bot_name} in robots.txt",
                evidence={"bot": bot_name, "status": "no_directive", "directive": None},
            )

    async def _check_robots_txt_direct(
        self,
        url: str,
        user_agent: str,
        criterion_id: str,
        bot_name: str,
    ) -> ScoringCriterionResult:
        """Check robots.txt directly for bots not in AIBotAccess schema (C4, C6).

        Fetches and caches robots.txt per domain, then checks if the given
        user agent is allowed to access the URL.

        Args:
            url: The page URL being checked.
            user_agent: The bot user-agent string (e.g., "OAI-SearchBot").
            criterion_id: Criterion ID (e.g., "C4").
            bot_name: Display name of the bot.

        Returns:
            ScoringCriterionResult with score 100 (allowed) or 0 (blocked).
        """
        purpose = BOT_PURPOSE.get(bot_name, "can access your content")

        try:
            robots_text, rp = await self._get_robots_txt(url)
        except Exception as e:
            logger.debug("Could not fetch robots.txt for {}: {}", url, str(e))
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=f"{bot_name} access",
                score=100,
                is_binary=True,
                human_summary=f"{bot_name}: ALLOWED (no robots.txt) -- {purpose}",
                technical_detail="robots.txt not accessible; assumed allowed",
                evidence={"bot": bot_name, "status": "no_robots_txt"},
            )

        # Check if the bot is mentioned in robots.txt
        bot_mentioned = user_agent.lower() in robots_text.lower()

        if bot_mentioned:
            can_fetch = rp.can_fetch(user_agent, url)
            if can_fetch:
                return ScoringCriterionResult(
                    criterion_id=criterion_id,
                    criterion_name=f"{bot_name} access",
                    score=100,
                    is_binary=True,
                    human_summary=f"{bot_name}: ALLOWED -- {purpose}",
                    technical_detail=f"robots.txt explicitly allows {bot_name}",
                    evidence={"bot": bot_name, "status": "allowed", "directive": "Allow"},
                )
            else:
                return ScoringCriterionResult(
                    criterion_id=criterion_id,
                    criterion_name=f"{bot_name} access",
                    score=0,
                    is_binary=True,
                    human_summary=f"{bot_name}: BLOCKED via robots.txt -- {purpose.replace('can', 'cannot')}",
                    technical_detail=f"robots.txt contains Disallow directive for {bot_name}",
                    evidence={"bot": bot_name, "status": "blocked", "directive": "Disallow"},
                )
        else:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=f"{bot_name} access",
                score=100,
                is_binary=True,
                human_summary=f"{bot_name}: ALLOWED (no specific directive) -- {purpose}",
                technical_detail=f"No Disallow directive for {bot_name} in robots.txt",
                evidence={"bot": bot_name, "status": "no_directive", "directive": None},
            )

    async def _get_robots_txt(self, url: str) -> tuple[str, RobotFileParser]:
        """Fetch and cache robots.txt for a domain.

        Args:
            url: Any URL on the domain.

        Returns:
            Tuple of (raw robots.txt text, parsed RobotFileParser).

        Raises:
            Exception: If robots.txt cannot be fetched or parsed.
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        base_url = f"{parsed.scheme}://{domain}"

        if domain in self._robots_cache:
            return self._robots_cache[domain]

        robots_url = f"{base_url}/robots.txt"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(robots_url)
            if response.status_code != 200:
                raise ValueError(f"robots.txt returned status {response.status_code}")

        robots_text = response.text
        rp = RobotFileParser()
        rp.parse(robots_text.splitlines())

        self._robots_cache[domain] = (robots_text, rp)
        return robots_text, rp

    async def _check_ssr(self, url: str, no_js_content: str) -> ScoringCriterionResult:
        """Check server-side rendering by comparing JS-rendered vs no-JS content.

        Launches Playwright Chromium headless (reusing a single browser instance),
        navigates to the URL, extracts text content with JS enabled, and compares
        word overlap against the no-JS content from the crawler.

        Args:
            url: The page URL to render with JS.
            no_js_content: Main content text extracted without JS execution.

        Returns:
            ScoringCriterionResult with gradient score (0-100) based on overlap ratio.
        """
        try:
            # Lazily initialize Playwright browser
            if self._browser is None:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)

            page = await self._browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)

                # Extract main content via JS
                js_content = await page.evaluate("""
                    () => {
                        const el = document.querySelector('main')
                            || document.querySelector('article')
                            || document.querySelector('body');
                        return el ? el.innerText : '';
                    }
                """)
            finally:
                await page.close()

            # Compare words
            js_words = set(js_content.lower().split()) if js_content else set()
            no_js_words = set(no_js_content.lower().split()) if no_js_content else set()

            if not js_words:
                overlap_ratio = 1.0  # No JS content means no JS dependency
            else:
                overlap = len(no_js_words & js_words)
                overlap_ratio = overlap / len(js_words)

            score = min(100, int(overlap_ratio * 100))

            # Determine quality label
            if score >= 90:
                label = "Excellent"
            elif score >= 70:
                label = "Good"
            elif score >= 50:
                label = "Moderate"
            else:
                label = "Poor"

            return ScoringCriterionResult(
                criterion_id="C9",
                criterion_name="Server-side rendering",
                score=score,
                is_binary=False,
                human_summary=f"{label} server-side rendering: {score}% of content available without JavaScript",
                technical_detail=f"JS-rendered words: {len(js_words)}, No-JS words: {len(no_js_words)}, Overlap: {round(overlap_ratio * 100, 1)}%",
                evidence={
                    "js_word_count": len(js_words),
                    "no_js_word_count": len(no_js_words),
                    "overlap_ratio": round(overlap_ratio, 3),
                    "score": score,
                },
            )

        except Exception as e:
            logger.warning("Playwright SSR check failed for {}: {}", url, str(e))
            return ScoringCriterionResult(
                criterion_id="C9",
                criterion_name="Server-side rendering",
                score=50,
                is_binary=False,
                human_summary="Could not render page with JavaScript -- score uncertain",
                technical_detail=f"Playwright failed: {str(e)[:200]}",
                evidence={"error": str(e)[:200]},
            )

    async def _check_ttfb(self, url: str) -> ScoringCriterionResult:
        """Measure Time to First Byte (TTFB) for the page.

        Scoring scale:
            <500ms = 100
            500-1000ms = 75-100 (linear)
            1000-1500ms = 50-75 (linear)
            1500-3000ms = 25-50 (linear)
            >3000ms = max(0, 25 - (ttfb-3000)/100)

        Args:
            url: The page URL to measure.

        Returns:
            ScoringCriterionResult with gradient score based on TTFB.
        """
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                response = await client.get(url)
                ttfb_ms = response.elapsed.total_seconds() * 1000

            # Compute score based on TTFB
            if ttfb_ms < 500:
                score = 100
            elif ttfb_ms < 1000:
                score = int(75 + (1000 - ttfb_ms) / 500 * 25)
            elif ttfb_ms < 1500:
                score = int(50 + (1500 - ttfb_ms) / 500 * 25)
            elif ttfb_ms < 3000:
                score = int(25 + (3000 - ttfb_ms) / 1500 * 25)
            else:
                score = max(0, int(25 - (ttfb_ms - 3000) / 100))

            # Determine quality label
            if ttfb_ms < 500:
                label = "Good"
            elif ttfb_ms < 1500:
                label = "Acceptable"
            elif ttfb_ms < 3000:
                label = "Slow"
            else:
                label = "Very slow"

            ttfb_rounded = round(ttfb_ms)

            return ScoringCriterionResult(
                criterion_id="C10",
                criterion_name="Response time (TTFB)",
                score=score,
                is_binary=False,
                human_summary=f"Page responds in {ttfb_rounded}ms -- {label} for AI crawlers",
                technical_detail=f"TTFB: {ttfb_rounded}ms, Score: {score}/100",
                evidence={
                    "ttfb_ms": ttfb_rounded,
                    "label": label,
                    "score": score,
                },
            )

        except Exception as e:
            logger.warning("TTFB check failed for {}: {}", url, str(e))
            return self._not_checked("C10", "Response time (TTFB)", f"Request failed: {str(e)[:200]}")

    async def _check_status_code(self, url: str) -> ScoringCriterionResult:
        """Check HTTP status code when accessed with a GPTBot-like User-Agent.

        Scoring:
            200 = 100
            301/302 = 75 (redirect acceptable but not ideal)
            403/404/5xx = 0

        Args:
            url: The page URL to check.

        Returns:
            ScoringCriterionResult with binary-style score based on status code.
        """
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) GPTBot/1.0"},
            ) as client:
                response = await client.get(url)
                status = response.status_code

            if status == 200:
                score = 100
                explanation = "OK -- page accessible to AI crawlers"
            elif status in (301, 302, 303, 307, 308):
                score = 75
                location = response.headers.get("location", "unknown")
                explanation = f"Redirect to {location} -- acceptable but adds latency"
            elif status == 403:
                score = 0
                explanation = "Forbidden -- server blocks AI bot User-Agent"
            elif status == 404:
                score = 0
                explanation = "Not Found -- page does not exist"
            elif status >= 500:
                score = 0
                explanation = "Server Error -- page is broken"
            else:
                score = 50
                explanation = f"Unexpected status -- may indicate issues"

            return ScoringCriterionResult(
                criterion_id="C11",
                criterion_name="HTTP status code",
                score=score,
                is_binary=True,
                human_summary=f"HTTP {status}: {explanation}",
                technical_detail=f"Status code: {status}, User-Agent: GPTBot-like",
                evidence={
                    "status_code": status,
                    "score": score,
                },
            )

        except Exception as e:
            logger.warning("Status code check failed for {}: {}", url, str(e))
            return self._not_checked("C11", "HTTP status code", f"Request failed: {str(e)[:200]}")

    async def _check_resource_blockage(self, url: str, crawl_data: dict) -> ScoringCriterionResult:
        """Check if robots.txt blocks CSS/JS resources that AI bots need for rendering.

        Looks for patterns like:
            Disallow: *.css
            Disallow: *.js
            Disallow: /static/
            Disallow: /assets/

        Scoring:
            100 = No resource blocks
            50 = Some resources blocked
            0 = Broad resource blocking

        Args:
            url: The page URL (used to fetch robots.txt if needed).
            crawl_data: Crawl result dict (not directly used but available).

        Returns:
            ScoringCriterionResult with gradient score based on resource blockage.
        """
        try:
            robots_text, _rp = await self._get_robots_txt(url)
        except Exception:
            # No robots.txt = no resource blocks
            return ScoringCriterionResult(
                criterion_id="C12",
                criterion_name="Resource blockage",
                score=100,
                is_binary=False,
                human_summary="No resource blockage detected (no robots.txt)",
                technical_detail="robots.txt not accessible; no resource blocks possible",
                evidence={"blocked_patterns": [], "robots_txt_available": False},
            )

        robots_lower = robots_text.lower()

        # Patterns that indicate resource blocking
        broad_blocks = [
            "disallow: *.css",
            "disallow: *.js",
            "disallow: /static",
            "disallow: /assets",
            "disallow: /_next/static",
            "disallow: /build",
            "disallow: /dist",
        ]

        # Narrower blocks that are less severe
        narrow_blocks = [
            "disallow: /wp-admin",
            "disallow: /cgi-bin",
        ]

        found_broad: list[str] = []
        found_narrow: list[str] = []

        for pattern in broad_blocks:
            if pattern in robots_lower:
                found_broad.append(pattern)

        for pattern in narrow_blocks:
            if pattern in robots_lower:
                found_narrow.append(pattern)

        if len(found_broad) >= 3:
            score = 0
            summary = "Broad resource blocking in robots.txt -- CSS, JS, and static assets blocked, severely degrading AI bot rendering"
        elif found_broad:
            score = 50
            summary = f"Some resources blocked in robots.txt ({', '.join(found_broad)}) -- may degrade AI bot rendering"
        else:
            score = 100
            summary = "No resource blockage detected -- AI bots can access CSS/JS for rendering"

        return ScoringCriterionResult(
            criterion_id="C12",
            criterion_name="Resource blockage",
            score=score,
            is_binary=False,
            human_summary=summary,
            technical_detail=f"Broad blocks: {found_broad}, Narrow blocks: {found_narrow}",
            evidence={
                "blocked_patterns_broad": found_broad,
                "blocked_patterns_narrow": found_narrow,
                "robots_txt_available": True,
                "score": score,
            },
        )

    async def cleanup(self) -> None:
        """Close Playwright browser and stop the playwright instance.

        Should be called when the scorer is no longer needed to release resources.
        """
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
