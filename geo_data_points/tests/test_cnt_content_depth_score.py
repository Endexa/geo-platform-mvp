"""
Test suite for CNT-007: Content Depth Score

Tests various scenarios to ensure accurate scoring and edge case handling.
"""

import asyncio
import pytest
from geo_data_points.measurements.cnt_content_depth_score import ContentDepthScoreMeasurement


class TestContentDepthScore:
    """Test cases for content depth measurement."""

    def setup_method(self):
        """Initialize measurement instance."""
        self.measurement = ContentDepthScoreMeasurement()

    @pytest.mark.asyncio
    async def test_minimal_content(self):
        """Test with minimal content."""
        html = """
        <html>
        <body>
            <h1>Title</h1>
            <p>Very short content.</p>
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert result['score'] < 30, "Minimal content should score low"
        assert 'shallow' in result['comment'].lower()
        print(f"✓ Minimal content test: Score={result['score']}, Comment={result['comment'][:100]}")

    @pytest.mark.asyncio
    async def test_comprehensive_content(self):
        """Test with comprehensive, well-structured content."""
        # Generate realistic comprehensive content
        html = """
        <html>
        <body>
            <article>
                <h1>Complete Guide to Machine Learning</h1>

                <p>Machine learning has revolutionized the technology landscape over the past decade.
                This comprehensive guide explores fundamental concepts, practical applications, and
                advanced techniques used by data scientists worldwide.</p>

                <h2>Introduction to Machine Learning</h2>
                <p>Machine learning is a subset of artificial intelligence that enables systems to
                learn and improve from experience without being explicitly programmed. It focuses on
                developing computer programs that can access data and use it to learn for themselves.</p>

                <h3>Types of Machine Learning</h3>
                <p>There are three primary types of machine learning algorithms:</p>
                <ul>
                    <li>Supervised Learning - Learning with labeled data</li>
                    <li>Unsupervised Learning - Finding patterns in unlabeled data</li>
                    <li>Reinforcement Learning - Learning through trial and error</li>
                </ul>

                <h3>Key Algorithms</h3>
                <p>The most important algorithms include linear regression, decision trees, random
                forests, support vector machines, and neural networks. Each algorithm has specific
                use cases and performance characteristics.</p>

                <h2>Supervised Learning</h2>
                <p>Supervised learning involves training a model on labeled data. The algorithm learns
                to map inputs to outputs based on example input-output pairs. Common applications include
                classification and regression tasks.</p>

                <h3>Classification Algorithms</h3>
                <p>Classification involves predicting categorical labels. Popular algorithms include:</p>
                <ol>
                    <li>Logistic Regression</li>
                    <li>Support Vector Machines (SVM)</li>
                    <li>Random Forests</li>
                    <li>Neural Networks</li>
                </ol>

                <h3>Regression Algorithms</h3>
                <p>Regression predicts continuous values. Key algorithms include linear regression,
                polynomial regression, and ridge regression. These are widely used in finance,
                economics, and scientific research.</p>

                <h2>Unsupervised Learning</h2>
                <p>Unsupervised learning finds hidden patterns in data without pre-labeled responses.
                It's used for clustering, dimensionality reduction, and anomaly detection.</p>

                <h3>Clustering Methods</h3>
                <p>Clustering groups similar data points together. Common methods include K-means,
                hierarchical clustering, and DBSCAN. These are valuable for customer segmentation
                and pattern recognition.</p>

                <h2>Deep Learning</h2>
                <p>Deep learning uses neural networks with multiple layers to learn hierarchical
                representations of data. It has achieved breakthrough results in computer vision,
                natural language processing, and speech recognition.</p>

                <blockquote>
                "Deep learning is not just a set of techniques, it's a way of thinking about learning
                from data." - Andrew Ng, Stanford University
                </blockquote>

                <h3>Neural Network Architectures</h3>
                <p>Popular architectures include:</p>
                <ul>
                    <li>Convolutional Neural Networks (CNNs) for image processing</li>
                    <li>Recurrent Neural Networks (RNNs) for sequential data</li>
                    <li>Transformers for natural language processing</li>
                    <li>Generative Adversarial Networks (GANs) for content generation</li>
                </ul>

                <h2>Practical Applications</h2>
                <p>Machine learning powers numerous real-world applications across industries.</p>

                <table>
                    <tr>
                        <th>Industry</th>
                        <th>Application</th>
                        <th>Algorithm Type</th>
                    </tr>
                    <tr>
                        <td>Healthcare</td>
                        <td>Disease Diagnosis</td>
                        <td>Classification</td>
                    </tr>
                    <tr>
                        <td>Finance</td>
                        <td>Fraud Detection</td>
                        <td>Anomaly Detection</td>
                    </tr>
                    <tr>
                        <td>Retail</td>
                        <td>Recommendation Systems</td>
                        <td>Collaborative Filtering</td>
                    </tr>
                </table>

                <h2>Model Evaluation</h2>
                <p>Evaluating machine learning models is crucial for understanding performance.
                Common metrics include accuracy, precision, recall, F1-score, and AUC-ROC curves.</p>

                <h3>Cross-Validation</h3>
                <p>Cross-validation is a resampling technique used to evaluate model performance on
                limited data. K-fold cross-validation is the most common approach, dividing data into
                k subsets and training k times.</p>

                <h2>Best Practices</h2>
                <p>Successful machine learning projects follow these principles:</p>
                <ol>
                    <li>Start with clean, quality data</li>
                    <li>Choose appropriate algorithms for the problem</li>
                    <li>Use proper train/test splits</li>
                    <li>Validate with cross-validation</li>
                    <li>Monitor for overfitting and underfitting</li>
                    <li>Document experiments and results</li>
                </ol>

                <h2>Future Trends</h2>
                <p>The field continues to evolve rapidly. Emerging trends include federated learning,
                explainable AI (XAI), AutoML, and quantum machine learning. These innovations will
                shape the next generation of AI systems.</p>

                <p>For more information, visit the
                <a href="https://arxiv.org/list/cs.LG/recent" target="_blank">arXiv ML repository</a>,
                <a href="https://papers.nips.cc/" target="_blank">NeurIPS proceedings</a>, and
                <a href="https://www.tensorflow.org/" target="_blank">TensorFlow documentation</a>.</p>

                <img src="/ml-diagram.png" alt="Machine Learning Pipeline Diagram" />
                <img src="/neural-network.png" alt="Neural Network Architecture" />
                <img src="/confusion-matrix.png" alt="Confusion Matrix Example" />
            </article>
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert result['score'] >= 80, "Comprehensive content should score high"
        assert 'excellent' in result['comment'].lower() or 'exceptional' in result['comment'].lower()
        print(f"✓ Comprehensive content test: Score={result['score']}")
        print(f"  Comment: {result['comment']}")

    @pytest.mark.asyncio
    async def test_moderate_content(self):
        """Test with moderate content depth."""
        html = """
        <html>
        <body>
            <h1>Introduction to Python</h1>

            <p>Python is a high-level programming language known for its simplicity and readability.
            It's widely used in web development, data science, and automation.</p>

            <h2>Why Python?</h2>
            <p>Python offers several advantages: easy to learn syntax, extensive standard library,
            and a large community of developers. These factors make it ideal for beginners and
            experts alike.</p>

            <h2>Basic Syntax</h2>
            <p>Python uses indentation to define code blocks. Here are some key concepts:</p>
            <ul>
                <li>Variables and data types</li>
                <li>Control structures (if, for, while)</li>
                <li>Functions and modules</li>
            </ul>

            <h2>Popular Applications</h2>
            <p>Python powers many modern applications including web frameworks like Django and Flask,
            data analysis with pandas and NumPy, and machine learning with TensorFlow and PyTorch.</p>

            <img src="/python-logo.png" alt="Python Logo" />
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert 40 < result['score'] < 80, "Moderate content should score in middle range"
        print(f"✓ Moderate content test: Score={result['score']}, Comment={result['comment'][:100]}")

    @pytest.mark.asyncio
    async def test_no_content(self):
        """Test with no meaningful content."""
        html = """
        <html>
        <body>
            <div>Empty</div>
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert result['score'] == 0, "No content should score 0"
        print(f"✓ No content test: Score={result['score']}")

    @pytest.mark.asyncio
    async def test_rich_multimedia(self):
        """Test content with rich multimedia elements."""
        html = """
        <html>
        <body>
            <h1>Visual Guide to Data Visualization</h1>

            <p>Data visualization transforms complex data into visual insights. This guide explores
            various chart types, tools, and best practices for creating effective visualizations that
            communicate data stories clearly and compellingly.</p>

            <h2>Chart Types</h2>
            <p>Different data requires different visualization approaches.</p>

            <img src="/bar-chart.png" alt="Bar Chart Example" />
            <img src="/line-chart.png" alt="Line Chart Example" />
            <img src="/scatter-plot.png" alt="Scatter Plot Example" />
            <img src="/pie-chart.png" alt="Pie Chart Example" />
            <img src="/heatmap.png" alt="Heatmap Example" />

            <h2>Video Tutorials</h2>
            <video src="/visualization-tutorial.mp4" controls>Tutorial Video</video>
            <video src="/advanced-techniques.mp4" controls>Advanced Techniques</video>

            <h2>Interactive Examples</h2>
            <p>Explore these interactive examples to understand concepts better.</p>

            <img src="/interactive-dashboard.png" alt="Interactive Dashboard" />
            <img src="/geographic-map.png" alt="Geographic Map Visualization" />
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert result['score'] > 40, "Rich multimedia should boost score"
        assert 'media' in result['comment'].lower() or 'images' in result['comment'].lower()
        print(f"✓ Rich multimedia test: Score={result['score']}")

    @pytest.mark.asyncio
    async def test_external_references(self):
        """Test content with many external references."""
        html = """
        <html>
        <body>
            <h1>Research on Climate Change</h1>

            <p>Climate change is one of the most critical challenges facing humanity. According to
            <a href="https://www.ipcc.ch/" target="_blank">IPCC reports</a>, global temperatures
            have risen significantly over the past century.</p>

            <h2>Scientific Evidence</h2>
            <p>Multiple studies from <a href="https://www.nature.com/" target="_blank">Nature</a>
            and <a href="https://www.science.org/" target="_blank">Science</a> journals confirm
            anthropogenic climate change.</p>

            <p>Research from <a href="https://www.nasa.gov/climate" target="_blank">NASA</a>,
            <a href="https://www.noaa.gov/" target="_blank">NOAA</a>, and
            <a href="https://www.wmo.int/" target="_blank">WMO</a> provides comprehensive data.</p>

            <h2>Impact Studies</h2>
            <p>Studies referenced by <a href="https://unfccc.int/" target="_blank">UNFCCC</a>
            and <a href="https://www.worldbank.org/climate" target="_blank">World Bank</a>
            highlight economic impacts.</p>

            <blockquote>
            "The evidence is overwhelming: climate change is real and human-caused."
            - Source: Nature Climate Change
            </blockquote>
        </body>
        </html>
        """
        result = await self.measurement.measure("https://example.com", html)

        assert 'reference' in result['comment'].lower() or 'external' in result['comment'].lower()
        print(f"✓ External references test: Score={result['score']}")


async def run_all_tests():
    """Run all test cases."""
    test_suite = TestContentDepthScore()

    print("\n" + "="*70)
    print("TESTING: CNT-007 Content Depth Score Measurement")
    print("="*70 + "\n")

    try:
        # Test 1: Minimal content
        test_suite.setup_method()
        await test_suite.test_minimal_content()

        # Test 2: Comprehensive content
        test_suite.setup_method()
        await test_suite.test_comprehensive_content()

        # Test 3: Moderate content
        test_suite.setup_method()
        await test_suite.test_moderate_content()

        # Test 4: No content
        test_suite.setup_method()
        await test_suite.test_no_content()

        # Test 5: Rich multimedia
        test_suite.setup_method()
        await test_suite.test_rich_multimedia()

        # Test 6: External references
        test_suite.setup_method()
        await test_suite.test_external_references()

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - Content Depth Score is production-ready!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {str(e)}\n")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
