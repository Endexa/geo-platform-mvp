from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import BrandVoiceConfig, VoiceVector, VoiceRule
from uuid import UUID
import openai
from app.core.config import settings
import re

openai.api_key = settings.OPENAI_API_KEY


class BrandVoiceService:
    def __init__(self, db: Session):
        self.db = db

    async def process_knowledge_base(self, config_id: UUID, text_content: str) -> int:
        """
        Process knowledge base text and create vector embeddings.
        Chunks text and stores embeddings in database.
        """
        # Chunk text (simple chunking by paragraphs for MVP)
        chunks = self._chunk_text(text_content, chunk_size=500)

        vector_count = 0
        for chunk in chunks:
            if len(chunk.strip()) < 50:  # Skip very small chunks
                continue

            # Generate embedding
            embedding = await self._generate_embedding(chunk)

            # Store in database
            voice_vector = VoiceVector(
                config_id=config_id,
                content_chunk=chunk,
                embedding=embedding
            )
            self.db.add(voice_vector)
            vector_count += 1

        self.db.commit()
        return vector_count

    def _chunk_text(self, text: str, chunk_size: int = 500) -> list:
        """
        Split text into chunks of approximately chunk_size characters.
        """
        # Split by paragraphs
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def _generate_embedding(self, text: str) -> list:
        """
        Generate embedding using OpenAI API.
        """
        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * 1536

    async def check_voice(self, text: str, config_id: UUID) -> dict:
        """
        Hybrid scoring: Vector similarity + Rule checking.
        """
        # 1. Vector Check (Score A)
        vector_score = await self._calculate_vector_similarity(text, config_id)

        # 2. Rule Check (Score B)
        rule_result = self._check_rules(text, config_id)
        rule_score = rule_result["score"]

        # 3. Hybrid Calculation: (A * 0.7) + (B * 0.3)
        hybrid_score = int((vector_score * 0.7) + (rule_score * 0.3))

        return {
            "hybrid_score": hybrid_score,
            "vector_score": vector_score,
            "rule_score": rule_score,
            "violations": rule_result["violations"],
            "suggestions": rule_result["suggestions"]
        }

    async def _calculate_vector_similarity(self, text: str, config_id: UUID) -> int:
        """
        Calculate cosine similarity against stored brand vectors.
        """
        # Generate embedding for input text
        input_embedding = await self._generate_embedding(text)

        # Query vectors for this config
        vectors = self.db.query(VoiceVector).filter(
            VoiceVector.config_id == config_id
        ).limit(10).all()  # Limit to top 10 for performance

        if not vectors:
            return 50  # Default if no vectors stored

        # Calculate cosine similarity using pgvector
        # Convert embedding to string format for SQL
        embedding_str = "[" + ",".join(map(str, input_embedding)) + "]"

        try:
            query = text(f"""
                SELECT 1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM voice_vectors
                WHERE config_id = :config_id
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT 5
            """)

            results = self.db.execute(query, {"config_id": str(config_id)}).fetchall()

            if results:
                # Average of top 5 similarities
                avg_similarity = sum(r[0] for r in results) / len(results)
                # Convert to 0-100 scale
                score = int(avg_similarity * 100)
                return max(0, min(100, score))

        except Exception as e:
            print(f"Error calculating similarity: {str(e)}")

        return 50  # Default fallback

    def _check_rules(self, text: str, config_id: UUID) -> dict:
        """
        Check text against brand voice rules.
        """
        rules = self.db.query(VoiceRule).filter(
            VoiceRule.config_id == config_id
        ).all()

        score = 100  # Start with perfect score
        violations = []
        suggestions = []

        text_lower = text.lower()

        for rule in rules:
            if rule.rule_type == "forbidden_word":
                if rule.value.lower() in text_lower:
                    score -= 20
                    violations.append({
                        "type": "forbidden_word",
                        "word": rule.value,
                        "suggestion": f"Remove or replace '{rule.value}'"
                    })

            elif rule.rule_type == "required_phrase":
                if rule.value.lower() not in text_lower:
                    score -= 10
                    violations.append({
                        "type": "missing_phrase",
                        "phrase": rule.value,
                        "suggestion": f"Consider adding '{rule.value}'"
                    })

            elif rule.rule_type == "tone_directive":
                # Simple tone checking (can be enhanced with NLP)
                suggestions.append({
                    "type": "tone",
                    "directive": rule.value
                })

        # Ensure score stays within 0-100
        score = max(0, min(100, score))

        return {
            "score": score,
            "violations": violations,
            "suggestions": suggestions
        }
