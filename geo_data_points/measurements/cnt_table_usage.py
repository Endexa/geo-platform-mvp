"""CNT-015: Table Usage - Data presentation"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class TableUsageMeasurement(BaseMeasurement):
    """Measures use of tables for data presentation."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            tables = soup.find_all('table')
            table_count = len(tables)

            # Check for proper table structure
            tables_with_headers = sum(1 for t in tables if t.find('th'))
            tables_with_caption = sum(1 for t in tables if t.find('caption'))

            # Score
            if table_count >= 3 and tables_with_headers >= 2:
                score = 100
            elif table_count >= 2 and tables_with_headers >= 1:
                score = 80
            elif table_count >= 1 and tables_with_headers >= 1:
                score = 60
            elif table_count >= 1:
                score = 40
            else:
                score = 100  # N/A if no data tables needed

            comment = f"{table_count} tables found" if table_count > 0 else "No tables (may not be needed)"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'CNT-015',
                    'table_count': table_count,
                    'with_headers': tables_with_headers,
                    'with_captions': tables_with_caption,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add header rows (th) to tables for accessibility'] if table_count > tables_with_headers else []
            }

        except Exception as e:
            logger.error(f"[CNT-015] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-015'}, 'recommendations': []}
