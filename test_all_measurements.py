"""Test runner for all 108 measurement scripts"""

import asyncio
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Sample test data
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Sample page for testing">
    <meta name="robots" content="index, follow">
    <title>Test Page - Sample Content</title>
    <link rel="canonical" href="https://example.com/test">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Test Org"}
    </script>
</head>
<body>
    <header>
        <h1>Main Title</h1>
        <nav><a href="/">Home</a></nav>
    </header>
    <main>
        <article>
            <h2>Section Title</h2>
            <p>This is a test paragraph with content.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <img src="test.jpg" alt="Test image">
        </article>
    </main>
</body>
</html>
"""

SAMPLE_URL = "https://example.com/test"
SAMPLE_METADATA = {
    'domain_authority': 50,
    'backlinks_count': 1000,
    'organic_traffic': 5000,
}


async def discover_measurements() -> List[str]:
    """Discover all measurement modules."""
    measurements_dir = Path('geo_data_points/measurements')
    modules = []

    for file in measurements_dir.glob('*.py'):
        if file.stem not in ['__init__', 'base_measurement']:
            modules.append(file.stem)

    return sorted(modules)


async def test_measurement(module_name: str) -> Dict[str, Any]:
    """Test a single measurement."""
    try:
        # Import module
        module = importlib.import_module(f'geo_data_points.measurements.{module_name}')

        # Find measurement class
        measurement_class = None
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.endswith('Measurement') and name != 'BaseMeasurement':
                measurement_class = obj
                break

        if not measurement_class:
            return {
                'module': module_name,
                'status': 'FAIL',
                'error': 'No measurement class found'
            }

        # Instantiate and run
        measurement = measurement_class()
        result = await measurement.measure(SAMPLE_URL, SAMPLE_HTML, SAMPLE_METADATA)

        # Validate result structure
        required_keys = ['score', 'comment', 'metadata', 'recommendations']
        missing_keys = [k for k in required_keys if k not in result]

        if missing_keys:
            return {
                'module': module_name,
                'status': 'FAIL',
                'error': f'Missing keys: {missing_keys}'
            }

        # Validate score range
        if not (0 <= result['score'] <= 100):
            return {
                'module': module_name,
                'status': 'FAIL',
                'error': f'Score out of range: {result["score"]}'
            }

        return {
            'module': module_name,
            'status': 'PASS',
            'score': result['score'],
            'measurement_id': result['metadata'].get('measurement_id', 'N/A')
        }

    except Exception as e:
        return {
            'module': module_name,
            'status': 'FAIL',
            'error': str(e)
        }


async def run_tests():
    """Run all measurement tests."""
    print("=" * 80)
    print("GEO PLATFORM - MEASUREMENT TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Discover all measurements
    modules = await discover_measurements()
    print(f"Discovered {len(modules)} measurement modules\n")

    # Run tests
    results = []
    for i, module in enumerate(modules, 1):
        print(f"[{i}/{len(modules)}] Testing {module}...", end=' ')
        result = await test_measurement(module)
        results.append(result)

        if result['status'] == 'PASS':
            print(f"✅ PASS (score: {result['score']}, id: {result['measurement_id']})")
        else:
            print(f"❌ FAIL - {result['error']}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')

    print(f"Total: {len(results)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")

    if failed > 0:
        print("\nFailed Tests:")
        for result in results:
            if result['status'] == 'FAIL':
                print(f"  - {result['module']}: {result['error']}")

    print("\n" + "=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return passed, failed


if __name__ == "__main__":
    asyncio.run(run_tests())
