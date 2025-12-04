"""
GEO Data Points Orchestrator

Main orchestrator that runs all data point measurements and stores results.
"""

import json
import importlib
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from db import (
    init_database,
    get_db_session,
    Analysis,
    DataPointResult
)
from utils import get_logger, get_config, validate_url, normalize_url


logger = get_logger("orchestrator")
config = get_config()


class GeoOrchestrator:
    """
    Orchestrator for running all GEO data point measurements.

    Workflow:
    1. Read data_points.json
    2. Create Analysis record
    3. Execute all measurement scripts
    4. Store results in database
    5. Update Analysis with summary
    """

    def __init__(self, url: str):
        """
        Initialize orchestrator.

        Args:
            url: Target URL to analyze
        """
        self.url = normalize_url(url)
        self.analysis_id = uuid.uuid4()
        self.data_points: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

        if not validate_url(self.url):
            raise ValueError(f"Invalid URL: {url}")

        logger.info(f"Initialized orchestrator for {self.url}")

    def load_data_points(self) -> int:
        """
        Load data points from JSON file.

        Returns:
            int: Number of data points loaded
        """
        data_points_file = config.DATA_POINTS_JSON

        if not data_points_file.exists():
            logger.error(f"data_points.json not found at {data_points_file}")
            raise FileNotFoundError(f"data_points.json not found")

        with open(data_points_file, 'r', encoding='utf-8') as f:
            self.data_points = json.load(f)

        logger.info(f"Loaded {len(self.data_points)} data points from JSON")
        return len(self.data_points)

    def _convert_data_point_name_to_module(self, data_point_name: str) -> str:
        """
        Convert data point name to Python module name.

        Examples:
        - "Robots.txt - GPTBot" → "robots_txt_gptbot"
        - "Schema.org Organization" → "schema_org_organization"
        - "Title Tag Optimization" → "title_tag_optimization"

        Args:
            data_point_name: Data point name from JSON

        Returns:
            str: Python module name
        """
        # Convert to lowercase, replace spaces/dashes/dots with underscores
        module_name = data_point_name.lower()
        module_name = module_name.replace(' - ', '_')
        module_name = module_name.replace('.', '_')
        module_name = module_name.replace(' ', '_')
        module_name = module_name.replace('-', '_')

        # Remove special characters
        allowed_chars = 'abcdefghijklmnopqrstuvwxyz0123456789_'
        module_name = ''.join(c for c in module_name if c in allowed_chars)

        return module_name

    def _get_measurement_class_name(self, module_name: str) -> str:
        """
        Convert module name to class name.

        Examples:
        - "robots_txt_gptbot" → "RobotsTxtGptbot"
        - "schema_org_organization" → "SchemaOrgOrganization"

        Args:
            module_name: Python module name

        Returns:
            str: Class name in PascalCase
        """
        parts = module_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        return class_name

    def run_measurement(self, data_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single data point measurement.

        Args:
            data_point: Data point configuration from JSON

        Returns:
            dict: Measurement result
        """
        data_point_name = data_point['Data Point Name']
        module_name = self._convert_data_point_name_to_module(data_point_name)

        logger.measurement_start(data_point_name, self.url)

        try:
            # Import measurement module
            module_path = f"scripts.{module_name}"
            module = importlib.import_module(module_path)

            # Get measurement class
            class_name = self._get_measurement_class_name(module_name)
            measurement_class = getattr(module, class_name)

            # Run measurement
            measurement = measurement_class(self.url)
            result = measurement.run()

            # Add data point metadata
            result['data_point_name'] = data_point_name
            result['module'] = data_point['Module']
            result['priority'] = data_point['Priority']
            result['measurement_method'] = data_point.get('Measurement Method', '')
            result['automation_level'] = data_point.get('Automation', '')

            return result

        except ImportError as e:
            logger.warning(f"Script not found for {data_point_name}: {module_name}.py - {str(e)}")
            return {
                'data_point_name': data_point_name,
                'module': data_point['Module'],
                'priority': data_point['Priority'],
                'score': 0.0,
                'comment': f'Script not implemented yet: {module_name}.py',
                'metadata': {},
                'execution_time_ms': 0.0,
                'timestamp': datetime.utcnow().isoformat(),
                'success': False,
                'error_message': f'Module not found: {module_name}',
                'measurement_method': data_point.get('Measurement Method', ''),
                'automation_level': data_point.get('Automation', '')
            }
        except Exception as e:
            logger.error(f"Error running {data_point_name}: {str(e)}", exc_info=True)
            return {
                'data_point_name': data_point_name,
                'module': data_point['Module'],
                'priority': data_point['Priority'],
                'score': 0.0,
                'comment': f'Measurement failed: {str(e)}',
                'metadata': {},
                'execution_time_ms': 0.0,
                'timestamp': datetime.utcnow().isoformat(),
                'success': False,
                'error_message': str(e),
                'measurement_method': data_point.get('Measurement Method', ''),
                'automation_level': data_point.get('Automation', '')
            }

    def run_all(self) -> uuid.UUID:
        """
        Run all data point measurements.

        Returns:
            UUID: Analysis ID
        """
        # Initialize database
        init_database()

        # Load data points
        total_count = self.load_data_points()

        # Create Analysis record
        with get_db_session() as db:
            analysis = Analysis(
                id=self.analysis_id,
                site_url=self.url,
                status="running",
                total_data_points=total_count
            )
            db.add(analysis)
            db.commit()
            logger.info(f"Created analysis record: {self.analysis_id}")

        # Run measurements
        successful = 0
        failed = 0

        for i, data_point in enumerate(self.data_points, 1):
            logger.info(f"[{i}/{total_count}] Processing: {data_point['Data Point Name']}")

            result = self.run_measurement(data_point)
            self.results.append(result)

            # Store result in database
            with get_db_session() as db:
                data_point_result = DataPointResult(
                    analysis_id=self.analysis_id,
                    data_point_name=result['data_point_name'],
                    module=result['module'],
                    priority=result['priority'],
                    score=result['score'],
                    comment=result['comment'],
                    measurement_method=result.get('measurement_method'),
                    automation_level=result.get('automation_level'),
                    execution_time_ms=result.get('execution_time_ms'),
                    error_message=result.get('error_message')
                )
                db.add(data_point_result)
                db.commit()

            if result.get('success', False):
                successful += 1
            else:
                failed += 1

        # Calculate average score
        scores = [r['score'] for r in self.results if r.get('success', False)]
        average_score = sum(scores) / len(scores) if scores else 0.0

        # Update Analysis record
        with get_db_session() as db:
            analysis = db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
            if analysis:
                analysis.status = "completed"
                analysis.completed_at = datetime.utcnow()
                analysis.successful_measurements = successful
                analysis.failed_measurements = failed
                analysis.average_score = round(average_score, 2)
                db.commit()

        logger.success(f"Analysis completed: {successful}/{total_count} successful")
        logger.info(f"Average GEO Score: {average_score:.2f}/100")

        return self.analysis_id

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of analysis results.

        Returns:
            dict: Summary statistics
        """
        if not self.results:
            return {}

        # Group by module
        modules = {}
        for result in self.results:
            module = result['module']
            if module not in modules:
                modules[module] = {'scores': [], 'count': 0}
            modules[module]['scores'].append(result['score'])
            modules[module]['count'] += 1

        # Calculate module averages
        module_averages = {
            module: {
                'average_score': sum(data['scores']) / len(data['scores']),
                'count': data['count']
            }
            for module, data in modules.items()
        }

        # Overall statistics
        all_scores = [r['score'] for r in self.results]
        successful = sum(1 for r in self.results if r.get('success', False))

        return {
            'analysis_id': str(self.analysis_id),
            'site_url': self.url,
            'total_data_points': len(self.results),
            'successful_measurements': successful,
            'failed_measurements': len(self.results) - successful,
            'average_score': sum(all_scores) / len(all_scores) if all_scores else 0.0,
            'module_scores': module_averages,
            'timestamp': datetime.utcnow().isoformat()
        }


def main():
    """
    Main entry point for orchestrator.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Run GEO Data Points analysis')
    parser.add_argument('url', help='Target URL to analyze')
    parser.add_argument('--summary', action='store_true', help='Print summary after analysis')

    args = parser.parse_args()

    try:
        orchestrator = GeoOrchestrator(args.url)
        analysis_id = orchestrator.run_all()

        print(f"\n{'=' * 60}")
        print(f"Analysis completed successfully!")
        print(f"Analysis ID: {analysis_id}")
        print(f"{'=' * 60}")

        if args.summary:
            summary = orchestrator.get_summary()
            print(f"\nSummary:")
            print(f"  URL: {summary['site_url']}")
            print(f"  Total Data Points: {summary['total_data_points']}")
            print(f"  Successful: {summary['successful_measurements']}")
            print(f"  Failed: {summary['failed_measurements']}")
            print(f"  Average GEO Score: {summary['average_score']:.2f}/100")
            print(f"\nModule Scores:")
            for module, data in summary['module_scores'].items():
                print(f"  {module}: {data['average_score']:.2f}/100 ({data['count']} data points)")

    except Exception as e:
        logger.error(f"Orchestrator failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
