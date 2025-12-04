#!/usr/bin/env python3
"""
Test Individual Measurement Scripts

Tests the implemented measurement scripts without requiring database.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from scripts.robots_txt_gptbot import RobotsTxtGPTBot
from scripts.robots_txt_claudebot import RobotsTxtClaudeBot
from scripts.schema_org_organization import SchemaOrgOrganization
from scripts.response_time import ResponseTime
from scripts.title_tag_optimization import TitleTagOptimization
from utils import get_logger


logger = get_logger("test_measurements")


def test_measurement(measurement_class, url: str):
    """
    Test a single measurement class.

    Args:
        measurement_class: Measurement class to test
        url: Target URL
    """
    try:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing: {measurement_class.__name__}")
        logger.info(f"URL: {url}")
        logger.info(f"{'=' * 60}")

        measurement = measurement_class(url)
        result = measurement.run()

        print(f"\n✓ {measurement_class.__name__}")
        print(f"  Score: {result['score']:.2f}/100")
        print(f"  Comment: {result['comment']}")
        print(f"  Execution Time: {result.get('execution_time_ms', 0):.0f}ms")
        print(f"  Success: {result.get('success', False)}")

        if result.get('metadata'):
            print(f"  Metadata:")
            for key, value in result['metadata'].items():
                if key not in ['schema_data']:  # Skip large data
                    print(f"    - {key}: {value}")

        return result

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        print(f"\n✗ {measurement_class.__name__} - FAILED")
        print(f"  Error: {str(e)}")
        return None


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(description='Test GEO measurement scripts')
    parser.add_argument('url', nargs='?', default='https://anthropic.com', help='Target URL to test (default: anthropic.com)')

    args = parser.parse_args()
    url = args.url

    logger.info(f"Starting measurement tests for: {url}")

    # List of implemented measurements
    measurements = [
        RobotsTxtGPTBot,
        RobotsTxtClaudeBot,
        SchemaOrgOrganization,
        ResponseTime,
        TitleTagOptimization
    ]

    results = []
    successful = 0
    failed = 0

    for measurement_class in measurements:
        result = test_measurement(measurement_class, url)
        if result and result.get('success', False):
            successful += 1
            results.append(result)
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total Tests: {len(measurements)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if results:
        average_score = sum(r['score'] for r in results) / len(results)
        total_time = sum(r.get('execution_time_ms', 0) for r in results)

        print(f"\nAverage Score: {average_score:.2f}/100")
        print(f"Total Execution Time: {total_time:.0f}ms ({total_time/1000:.2f}s)")

        print(f"\nIndividual Scores:")
        for result in results:
            print(f"  - {result.get('data_point_name', 'Unknown')}: {result['score']:.2f}/100")


if __name__ == "__main__":
    main()
