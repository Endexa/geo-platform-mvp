from sqlalchemy.orm import Session
from app.models import Analysis, Recommendation
from uuid import UUID
import openai
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY


class OptimizerService:
    def __init__(self, db: Session):
        self.db = db

    async def generate_recommendations(self, analysis_id: UUID):
        """
        Generate AI-powered recommendations using RAG approach.
        """
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            raise ValueError("Analysis not found")

        # Get content from raw_data
        url = analysis.raw_data.get("url", "")
        content_length = analysis.raw_data.get("content_length", 0)

        # Prepare prompt for GPT
        prompt = f"""
        You are a GEO (Generative Engine Optimization) expert.

        Analyze this website performance:
        - URL: {url}
        - GEO Score: {analysis.geo_score}/100
        - Visibility Score: {analysis.visibility_score}/100
        - Readability Score: {analysis.readability_score}/100
        - Authority Score: {analysis.authority_score}/100
        - Content Length: {content_length} characters

        Identify 3 critical gaps compared to top-ranking AI answers and provide actionable recommendations.

        Return a JSON array with this structure:
        [
            {{
                "category": "content" | "technical" | "metadata",
                "severity": "high" | "medium" | "low",
                "issue": "Brief description of the issue",
                "action_plan": "Detailed step-by-step fix",
                "impact_score": "+XX pts" (estimated GEO score improvement)
            }}
        ]
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a GEO optimization expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse recommendations
            import json
            recommendations_data = json.loads(response.choices[0].message.content)

            # Handle both array and object responses
            if isinstance(recommendations_data, dict) and "recommendations" in recommendations_data:
                recommendations_list = recommendations_data["recommendations"]
            elif isinstance(recommendations_data, list):
                recommendations_list = recommendations_data
            else:
                recommendations_list = [recommendations_data]

            # Store in database
            for rec_data in recommendations_list:
                recommendation = Recommendation(
                    analysis_id=analysis_id,
                    category=rec_data.get("category", "content"),
                    severity=rec_data.get("severity", "medium"),
                    issue=rec_data.get("issue", ""),
                    action_plan=rec_data.get("action_plan", ""),
                    impact_score=rec_data.get("impact_score", "+10pts")
                )
                self.db.add(recommendation)

            self.db.commit()

        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            # Create fallback recommendations
            self._create_fallback_recommendations(analysis_id)

    def _create_fallback_recommendations(self, analysis_id: UUID):
        """
        Create generic recommendations if AI fails.
        """
        fallback_recs = [
            {
                "category": "content",
                "severity": "high",
                "issue": "Content optimization needed",
                "action_plan": "Improve content structure with clear headings and concise paragraphs",
                "impact_score": "+15pts"
            },
            {
                "category": "technical",
                "severity": "medium",
                "issue": "Schema markup missing",
                "action_plan": "Implement Schema.org structured data for better AI understanding",
                "impact_score": "+12pts"
            },
            {
                "category": "metadata",
                "severity": "medium",
                "issue": "Meta descriptions need optimization",
                "action_plan": "Write compelling meta descriptions with target keywords",
                "impact_score": "+10pts"
            }
        ]

        for rec_data in fallback_recs:
            recommendation = Recommendation(
                analysis_id=analysis_id,
                category=rec_data["category"],
                severity=rec_data["severity"],
                issue=rec_data["issue"],
                action_plan=rec_data["action_plan"],
                impact_score=rec_data["impact_score"]
            )
            self.db.add(recommendation)

        self.db.commit()

    async def optimize_content(self, recommendation: Recommendation) -> str:
        """
        Generate optimized content based on recommendation.
        """
        prompt = f"""
        Based on this recommendation:
        Issue: {recommendation.issue}
        Action Plan: {recommendation.action_plan}

        Generate optimized content (1-2 paragraphs) that implements this recommendation.
        Be specific and actionable.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content optimization expert."},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error generating optimized content: {str(e)}"
