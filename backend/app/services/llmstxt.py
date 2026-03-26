"""
llms.txt Generator Service — Creates and validates llms.txt files for AI crawler guidance.

The llms.txt standard is an emerging specification that helps AI crawlers
understand your site structure and find your most important content.

Location: /llms.txt (root of domain)
Extended: /llms-full.txt (detailed version)

Format:
    # Site Name
    > Brief description

    ## Section Name
    - [Page Title](url): Description

    ## Contact
    - Email: contact@example.com
    - Website: https://example.com
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from loguru import logger


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def validate_llmstxt(url: str) -> Dict:
    """
    Check if llms.txt exists and validate its format.

    Args:
        url: The website URL to check

    Returns:
        Dictionary with validation results
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    llms_url = f"{base_url}/llms.txt"
    llms_full_url = f"{base_url}/llms-full.txt"

    result = {
        "url": llms_url,
        "exists": False,
        "format_valid": False,
        "has_title": False,
        "has_description": False,
        "has_sections": False,
        "has_links": False,
        "section_count": 0,
        "link_count": 0,
        "content": "",
        "issues": [],
        "suggestions": [],
        "full_version": {
            "url": llms_full_url,
            "exists": False,
        },
    }

    # Check llms.txt
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(llms_url, headers=DEFAULT_HEADERS, follow_redirects=True)

            if response.status_code == 200:
                result["exists"] = True
                result["content"] = response.text
                content = response.text

                # Validate format
                lines = content.strip().split("\n")

                # Check for title (# at start)
                if lines and lines[0].startswith("# "):
                    result["has_title"] = True
                else:
                    result["issues"].append("Missing title (should start with '# Site Name')")

                # Check for description (> blockquote)
                for line in lines:
                    if line.startswith("> "):
                        result["has_description"] = True
                        break
                if not result["has_description"]:
                    result["issues"].append("Missing description (use '> Brief description')")

                # Check for sections (## headings)
                sections = [l for l in lines if l.startswith("## ")]
                result["section_count"] = len(sections)
                result["has_sections"] = len(sections) > 0
                if not result["has_sections"]:
                    result["issues"].append("No sections found (use '## Section Name')")

                # Check for links
                link_pattern = r"- \[.+\]\(.+\)"
                links = re.findall(link_pattern, content)
                result["link_count"] = len(links)
                result["has_links"] = len(links) > 0
                if not result["has_links"]:
                    result["issues"].append("No page links found (use '- [Page Title](url): Description')")

                # Overall format validity
                result["format_valid"] = (
                    result["has_title"]
                    and result["has_description"]
                    and result["has_sections"]
                    and result["has_links"]
                )

                # Suggestions
                if result["link_count"] < 5:
                    result["suggestions"].append("Consider adding more key pages (aim for 10-20)")
                if result["section_count"] < 2:
                    result["suggestions"].append("Add more sections to organize content types")
                if "contact" not in content.lower():
                    result["suggestions"].append("Add a Contact section with email and location")
                if "key fact" not in content.lower() and "about" not in content.lower():
                    result["suggestions"].append("Add key facts about your business/service")

            else:
                result["issues"].append(f"llms.txt returned status {response.status_code}")

    except Exception as e:
        logger.error(f"Error fetching llms.txt from {llms_url}: {e}")
        result["issues"].append(f"Error fetching llms.txt: {str(e)}")

    # Check llms-full.txt
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(llms_full_url, headers=DEFAULT_HEADERS, follow_redirects=True)
            if response.status_code == 200:
                result["full_version"]["exists"] = True
    except Exception:
        pass

    return result


async def generate_llmstxt(url: str, max_pages: int = 30) -> Dict:
    """
    Generate an llms.txt file by crawling the site.

    Args:
        url: The website URL to analyze
        max_pages: Maximum number of pages to crawl

    Returns:
        Dictionary with generated llms.txt content and metadata
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "generated_llmstxt": "",
        "generated_llmstxt_full": "",
        "pages_analyzed": 0,
        "sections": {},
    }

    # Fetch homepage
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True)
            soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        logger.error(f"Failed to fetch homepage for llms.txt generation: {e}")
        result["error"] = f"Failed to fetch homepage: {str(e)}"
        return result

    # Extract site name and description
    title = soup.find("title")
    site_name = title.get_text(strip=True).split("|")[0].split("-")[0].strip() if title else parsed.netloc
    meta_desc = soup.find("meta", attrs={"name": "description"})
    site_description = meta_desc.get("content", "") if meta_desc else f"Official website of {site_name}"

    # Discover and categorize pages
    pages = {
        "Main Pages": [],
        "Products & Services": [],
        "Resources & Blog": [],
        "Company": [],
        "Support": [],
    }

    # Crawl internal links
    seen_urls = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        link_text = link.get_text(strip=True)

        if not link_text or len(link_text) < 2:
            continue

        parsed_href = urlparse(href)
        if parsed_href.netloc != parsed.netloc:
            continue
        if href in seen_urls:
            continue
        if any(ext in href for ext in [".pdf", ".jpg", ".png", ".gif", ".css", ".js"]):
            continue
        if "#" in href and href.split("#")[0] in seen_urls:
            continue

        seen_urls.add(href)
        path = parsed_href.path.lower()

        # Categorize
        page_entry = {"url": href, "title": link_text}

        if any(kw in path for kw in ["/pricing", "/feature", "/product", "/solution", "/demo"]):
            pages["Products & Services"].append(page_entry)
        elif any(kw in path for kw in ["/blog", "/article", "/resource", "/guide", "/learn", "/docs", "/documentation"]):
            pages["Resources & Blog"].append(page_entry)
        elif any(kw in path for kw in ["/about", "/team", "/career", "/contact", "/press", "/partner"]):
            pages["Company"].append(page_entry)
        elif any(kw in path for kw in ["/help", "/support", "/faq", "/status"]):
            pages["Support"].append(page_entry)
        elif path in ["/", ""] or any(kw in path for kw in ["/home", "/index"]):
            if href != base_url and href != base_url + "/":
                pages["Main Pages"].append(page_entry)
        else:
            pages["Main Pages"].append(page_entry)

        if len(seen_urls) >= max_pages:
            break

    result["pages_analyzed"] = len(seen_urls)

    # Generate llms.txt (concise version)
    llms_lines = [
        f"# {site_name}",
        f"> {site_description}",
        "",
    ]

    for section, section_pages in pages.items():
        if section_pages:
            llms_lines.append(f"## {section}")
            # Limit to top 10 per section for concise version
            for page in section_pages[:10]:
                llms_lines.append(f"- [{page['title']}]({page['url']})")
            llms_lines.append("")

    # Add contact section placeholder
    llms_lines.extend([
        "## Contact",
        f"- Website: {base_url}",
        f"- Email: contact@{parsed.netloc}",
        "",
    ])

    result["generated_llmstxt"] = "\n".join(llms_lines)

    # Generate llms-full.txt (detailed version with descriptions)
    full_lines = [
        f"# {site_name}",
        f"> {site_description}",
        "",
    ]

    for section, section_pages in pages.items():
        if section_pages:
            full_lines.append(f"## {section}")
            for page in section_pages:
                # Try to fetch page description (limited to avoid timeout)
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        page_resp = await client.get(page["url"], headers=DEFAULT_HEADERS, follow_redirects=True)
                        page_soup = BeautifulSoup(page_resp.text, "lxml")
                        page_meta = page_soup.find("meta", attrs={"name": "description"})
                        page_desc = page_meta.get("content", "") if page_meta else ""
                        if page_desc:
                            full_lines.append(f"- [{page['title']}]({page['url']}): {page_desc}")
                        else:
                            full_lines.append(f"- [{page['title']}]({page['url']})")
                except Exception:
                    full_lines.append(f"- [{page['title']}]({page['url']})")
            full_lines.append("")

    full_lines.extend([
        "## Contact",
        f"- Website: {base_url}",
        f"- Email: contact@{parsed.netloc}",
        "",
    ])

    result["generated_llmstxt_full"] = "\n".join(full_lines)
    result["sections"] = {k: len(v) for k, v in pages.items()}

    return result
