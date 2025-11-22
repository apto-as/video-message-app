"""
Test Report Generator
Author: Hestia (Security Guardian)
Date: 2025-11-07

Purpose: Generate comprehensive test reports with metrics and statistics.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class TestReport:
    """Generate comprehensive test execution reports"""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.end_time = None

    def add_result(
        self,
        test_name: str,
        success: bool,
        duration_ms: float,
        error: str = None,
        category: str = "e2e"
    ):
        """Add a test result"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "duration_ms": duration_ms,
            "error": error,
            "category": category,
            "timestamp": datetime.utcnow().isoformat()
        })

    def finalize(self):
        """Finalize report"""
        self.end_time = time.time()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test execution summary"""
        if not self.end_time:
            self.finalize()

        total_tests = len(self.test_results)
        successful = sum(1 for r in self.test_results if r["success"])
        failed = total_tests - successful

        success_rate = (successful / total_tests * 100) if total_tests > 0 else 0

        # Calculate latency stats
        durations = [r["duration_ms"] for r in self.test_results]
        avg_latency = sum(durations) / len(durations) if durations else 0
        p50_latency = sorted(durations)[len(durations) // 2] if durations else 0
        p95_latency = sorted(durations)[int(len(durations) * 0.95)] if durations else 0
        p99_latency = sorted(durations)[int(len(durations) * 0.99)] if durations else 0

        # Category breakdown
        categories = {}
        for result in self.test_results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0, "failed": 0}
            categories[cat]["total"] += 1
            if result["success"]:
                categories[cat]["success"] += 1
            else:
                categories[cat]["failed"] += 1

        return {
            "summary": {
                "total_tests": total_tests,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{success_rate:.2f}%",
                "total_duration_s": self.end_time - self.start_time
            },
            "latency": {
                "average_ms": avg_latency,
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
                "min_ms": min(durations) if durations else 0,
                "max_ms": max(durations) if durations else 0
            },
            "categories": categories,
            "failed_tests": [
                {
                    "name": r["test_name"],
                    "error": r["error"],
                    "duration_ms": r["duration_ms"]
                }
                for r in self.test_results if not r["success"]
            ]
        }

    def export_json(self, output_path: Path):
        """Export report as JSON"""
        summary = self.generate_summary()
        summary["results"] = self.test_results

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

    def export_markdown(self, output_path: Path):
        """Export report as Markdown"""
        summary = self.generate_summary()

        md = []
        md.append("# E2E Test Report")
        md.append("")
        md.append(f"**Generated**: {datetime.utcnow().isoformat()}Z")
        md.append("")

        # Summary
        md.append("## Summary")
        md.append("")
        md.append(f"- **Total Tests**: {summary['summary']['total_tests']}")
        md.append(f"- **Successful**: {summary['summary']['successful']}")
        md.append(f"- **Failed**: {summary['summary']['failed']}")
        md.append(f"- **Success Rate**: {summary['summary']['success_rate']}")
        md.append(f"- **Total Duration**: {summary['summary']['total_duration_s']:.2f}s")
        md.append("")

        # Latency
        md.append("## Latency Metrics")
        md.append("")
        md.append("| Metric | Value (ms) |")
        md.append("|--------|------------|")
        md.append(f"| Average | {summary['latency']['average_ms']:.2f} |")
        md.append(f"| P50 | {summary['latency']['p50_ms']:.2f} |")
        md.append(f"| P95 | {summary['latency']['p95_ms']:.2f} |")
        md.append(f"| P99 | {summary['latency']['p99_ms']:.2f} |")
        md.append(f"| Min | {summary['latency']['min_ms']:.2f} |")
        md.append(f"| Max | {summary['latency']['max_ms']:.2f} |")
        md.append("")

        # Categories
        md.append("## Test Categories")
        md.append("")
        md.append("| Category | Total | Success | Failed | Success Rate |")
        md.append("|----------|-------|---------|--------|--------------|")
        for cat, stats in summary["categories"].items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            md.append(f"| {cat} | {stats['total']} | {stats['success']} | {stats['failed']} | {rate:.1f}% |")
        md.append("")

        # Failed tests
        if summary["failed_tests"]:
            md.append("## Failed Tests")
            md.append("")
            for test in summary["failed_tests"]:
                md.append(f"### {test['name']}")
                md.append(f"- **Error**: {test['error']}")
                md.append(f"- **Duration**: {test['duration_ms']:.2f}ms")
                md.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(md))

    def export_html(self, output_path: Path):
        """Export report as HTML"""
        summary = self.generate_summary()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>E2E Test Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            background-color: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #4CAF50;
        }}
        .metric.failed {{
            border-left-color: #f44336;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            font-size: 14px;
            color: #777;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .success {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .failed {{
            color: #f44336;
            font-weight: bold;
        }}
        .error-box {{
            background-color: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin: 10px 0;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>E2E Test Report</h1>
        <p class="timestamp">Generated: {datetime.utcnow().isoformat()}Z</p>

        <h2>Summary</h2>
        <div class="summary">
            <div class="metric">
                <div class="metric-value">{summary['summary']['total_tests']}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value success">{summary['summary']['successful']}</div>
                <div class="metric-label">Successful</div>
            </div>
            <div class="metric failed">
                <div class="metric-value failed">{summary['summary']['failed']}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary['summary']['success_rate']}</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary['summary']['total_duration_s']:.2f}s</div>
                <div class="metric-label">Total Duration</div>
            </div>
        </div>

        <h2>Latency Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value (ms)</th>
            </tr>
            <tr>
                <td>Average</td>
                <td>{summary['latency']['average_ms']:.2f}</td>
            </tr>
            <tr>
                <td>P50 (Median)</td>
                <td>{summary['latency']['p50_ms']:.2f}</td>
            </tr>
            <tr>
                <td>P95</td>
                <td>{summary['latency']['p95_ms']:.2f}</td>
            </tr>
            <tr>
                <td>P99</td>
                <td>{summary['latency']['p99_ms']:.2f}</td>
            </tr>
            <tr>
                <td>Min</td>
                <td>{summary['latency']['min_ms']:.2f}</td>
            </tr>
            <tr>
                <td>Max</td>
                <td>{summary['latency']['max_ms']:.2f}</td>
            </tr>
        </table>

        <h2>Test Categories</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Total</th>
                <th>Success</th>
                <th>Failed</th>
                <th>Success Rate</th>
            </tr>
"""

        for cat, stats in summary["categories"].items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            html += f"""
            <tr>
                <td>{cat}</td>
                <td>{stats['total']}</td>
                <td class="success">{stats['success']}</td>
                <td class="failed">{stats['failed']}</td>
                <td>{rate:.1f}%</td>
            </tr>
"""

        html += """
        </table>
"""

        if summary["failed_tests"]:
            html += """
        <h2>Failed Tests</h2>
"""
            for test in summary["failed_tests"]:
                html += f"""
        <div class="error-box">
            <strong>{test['name']}</strong><br>
            <strong>Error:</strong> {test['error']}<br>
            <strong>Duration:</strong> {test['duration_ms']:.2f}ms
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        with open(output_path, "w") as f:
            f.write(html)


if __name__ == "__main__":
    # Example usage
    report = TestReport()

    # Add sample results
    report.add_result("test_complete_pipeline", True, 15234.5, category="e2e")
    report.add_result("test_no_person_detected", True, 8123.2, category="e2e")
    report.add_result("test_invalid_image", True, 234.1, category="e2e")
    report.add_result("test_sql_injection", True, 123.4, category="security")
    report.add_result("test_xss_attack", True, 98.7, category="security")
    report.add_result("test_audio_bomb", False, 5123.2, "Security violation", category="security")

    # Export reports
    output_dir = Path(__file__).parent.parent.parent / "test_reports"
    output_dir.mkdir(exist_ok=True)

    report.export_json(output_dir / "test_report.json")
    report.export_markdown(output_dir / "test_report.md")
    report.export_html(output_dir / "test_report.html")

    print("✅ Test reports generated:")
    print(f"   - {output_dir / 'test_report.json'}")
    print(f"   - {output_dir / 'test_report.md'}")
    print(f"   - {output_dir / 'test_report.html'}")
