from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
import requests
import textstat
from datetime import datetime
from app.models import Analysis
from uuid import UUID


class AnalyzerService:
    def __init__(self, db: Session):
        self.db = db

    def run_analysis(self, analysis_id: UUID, url: str, keywords: list):
        """
        Main analysis pipeline.
        Background task - synchronous implementation for MVP.
        """
        try:
            analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
            analysis.status = "processing"
            self.db.commit()

            # 1. Fetch and parse content
            content = self.fetch_content(url)

            # 2. Calculate scores
            visibility_score = self.calculate_visibility_score(content, keywords)
            readability_score = self.calculate_readability_score(content)
            authority_score = self.calculate_authority_score(url)  # Mock for MVP

            # 3. Calculate GEO score (weighted average)
            geo_score = int(
                (visibility_score * 0.4) +
                (readability_score * 0.3) +
                (authority_score * 0.3)
            )

            # 4. Update analysis
            analysis.status = "completed"
            analysis.geo_score = geo_score
            analysis.visibility_score = visibility_score
            analysis.readability_score = readability_score
            analysis.authority_score = authority_score
            analysis.raw_data = {
                "url": url,
                "keywords": keywords,
                "content_length": len(content["text"]),
                "h1_count": content["h1_count"],
                "h2_count": content["h2_count"]
            }
            analysis.completed_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            analysis.status = "failed"
            analysis.raw_data = {"error": str(e)}
            self.db.commit()
            raise

    def fetch_content(self, url: str) -> dict:
        """
        Fetch and parse HTML content.
        For MVP: using requests + BeautifulSoup.
        For production: upgrade to Playwright for JS rendering.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GEOBot/1.0)"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract main content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator=' ', strip=True)

            # Count headings
            h1_count = len(soup.find_all('h1'))
            h2_count = len(soup.find_all('h2'))

            # Get all headings text
            headings = []
            for h in soup.find_all(['h1', 'h2', 'h3']):
                headings.append(h.get_text(strip=True))

            return {
                "text": text,
                "h1_count": h1_count,
                "h2_count": h2_count,
                "headings": headings
            }

        except Exception as e:
            raise Exception(f"Failed to fetch content: {str(e)}")

    def calculate_visibility_score(self, content: dict, keywords: list) -> int:
        """
        Visibility Score: (Keywords found in H1/H2 / Total Keywords) * 100
        """
        if not keywords:
            return 50  # Default if no keywords provided

        headings_text = ' '.join(content["headings"]).lower()
        keywords_found = sum(1 for kw in keywords if kw.lower() in headings_text)

        score = (keywords_found / len(keywords)) * 100
        return int(min(score, 100))

    def calculate_readability_score(self, content: dict) -> int:
        """
        Readability Score: Flesch-Kincaid score normalized to 0-100.
        Higher score = more readable.
        """
        text = content["text"]

        if len(text) < 100:
            return 50  # Too short to analyze

        # Flesch Reading Ease (0-100, higher = easier)
        flesch_score = textstat.flesch_reading_ease(text)

        # Normalize to 0-100
        normalized = max(0, min(100, flesch_score))
        return int(normalized)

    def calculate_authority_score(self, url: str) -> int:
        """
        Authority Score: Mock implementation for MVP.
        In production: integrate with Moz API or Ahrefs for real backlink data.
        """
        # Mock scoring based on domain
        if any(domain in url for domain in ['.edu', '.gov', '.org']):
            return 85
        elif any(domain in url for domain in ['wikipedia', 'medium', 'forbes']):
            return 75
        else:
            # Random score for demo
            import random
            return random.randint(40, 70)
