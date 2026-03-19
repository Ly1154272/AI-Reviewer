"""Tests for report generator."""

import json
import tempfile
import pytest
from pathlib import Path

from src.report.generator import ReportGenerator, ResultAggregator
from src.core.models import (
    Issue,
    IssueSource,
    ReviewReport,
    ReviewSummary,
    Severity,
    ReviewMode,
    AiAnalysis,
    ReportConfig,
)


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_json_report(self):
        """Test generating JSON report."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            branch="main",
            mode=ReviewMode.INCREMENTAL,
        )
        
        report.add_issue(Issue(
            source=IssueSource.P3C,
            file="UserService.java",
            line=42,
            severity=Severity.WARNING,
            message="类名应该以 Service 结尾",
        ))
        
        config = ReportConfig(
            output_format="json",
            output_path="test.json",
        )
        
        generator = ReportGenerator(config)
        json_output = generator.generate(report)
        
        result = json.loads(json_output)
        assert result["repository"] == "https://github.com/test/repo"
        assert result["summary"]["total_issues"] == 1
        assert result["summary"]["warning"] == 1

    def test_generate_markdown_report(self):
        """Test generating Markdown report."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.FULL,
        )
        
        report.add_issue(Issue(
            source=IssueSource.AI,
            file="Test.java",
            line=10,
            severity=Severity.CRITICAL,
            message="安全问题：硬编码密码",
        ))
        
        config = ReportConfig(
            output_format="markdown",
            output_path="test.md",
        )
        
        generator = ReportGenerator(config)
        md_output = generator.generate(report)
        
        assert "# Code Review Report" in md_output
        assert "## Summary" in md_output
        assert "Test.java" in md_output
        assert "安全问题：硬编码密码" in md_output


class TestResultAggregator:
    """Tests for ResultAggregator."""

    def test_aggregate_empty(self):
        """Test aggregating empty issues."""
        result = ResultAggregator.aggregate([])
        assert len(result) == 0

    def test_aggregate_single_issue(self):
        """Test aggregating single issue."""
        issues = [Issue(
            source=IssueSource.AI,
            file="Test.java",
            severity=Severity.WARNING,
            message="Test",
        )]
        
        result = ResultAggregator.aggregate(issues)
        assert len(result) == 1

    def test_deduplicate_issues(self):
        """Test deduplicating issues."""
        issues = [
            Issue(
                source=IssueSource.P3C,
                file="Test.java",
                line=10,
                severity=Severity.WARNING,
                message="类名应该以 Service 结尾",
            ),
            Issue(
                source=IssueSource.AI,
                file="Test.java",
                line=10,
                severity=Severity.WARNING,
                message="类名应该以 Service 结尾",
            ),
        ]
        
        result = ResultAggregator.aggregate(issues)
        assert len(result) == 1

    def test_sort_by_severity(self):
        """Test sorting by severity."""
        issues = [
            Issue(
                source=IssueSource.AI,
                file="A.java",
                severity=Severity.INFO,
                message="Info",
            ),
            Issue(
                source=IssueSource.P3C,
                file="C.java",
                severity=Severity.CRITICAL,
                message="Critical",
            ),
            Issue(
                source=IssueSource.SPOTBUGS,
                file="B.java",
                severity=Severity.WARNING,
                message="Warning",
            ),
        ]
        
        result = ResultAggregator.aggregate(issues)
        
        assert result[0].severity == Severity.CRITICAL
        assert result[1].severity == Severity.WARNING
        assert result[2].severity == Severity.INFO

    def test_filter_false_positives(self):
        """Test filtering false positives."""
        issues = [
            Issue(
                source=IssueSource.P3C,
                file="Test.java",
                line=10,
                severity=Severity.WARNING,
                message="Test issue",
                ai_analysis=AiAnalysis(
                    is_false_positive=False,
                    confidence=0.9,
                ),
            ),
            Issue(
                source=IssueSource.SPOTBUGS,
                file="Test.java",
                line=20,
                severity=Severity.WARNING,
                message="False positive issue",
                ai_analysis=AiAnalysis(
                    is_false_positive=True,
                    confidence=0.95,
                ),
            ),
        ]
        
        result_with_fp = ResultAggregator.aggregate(issues, include_false_positives=True)
        assert len(result_with_fp) == 2
        
        result_without_fp = ResultAggregator.aggregate(issues, include_false_positives=False)
        assert len(result_without_fp) == 1
        assert result_without_fp[0].line == 10

    def test_summary_counts(self):
        """Test summary counts are correct."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.INCREMENTAL,
        )
        
        for i in range(3):
            report.add_issue(Issue(
                source=IssueSource.P3C,
                file=f"File{i}.java",
                severity=Severity.CRITICAL,
                message=f"Critical {i}",
            ))
        
        for i in range(5):
            report.add_issue(Issue(
                source=IssueSource.AI,
                file=f"File{i}.java",
                severity=Severity.WARNING,
                message=f"Warning {i}",
            ))
        
        for i in range(2):
            report.add_issue(Issue(
                source=IssueSource.SPOTBUGS,
                file=f"File{i}.java",
                severity=Severity.INFO,
                message=f"Info {i}",
            ))
        
        assert report.summary.total_issues == 10
        assert report.summary.critical == 3
        assert report.summary.warning == 5
        assert report.summary.info == 2
