"""Tests for core models."""

import pytest
from datetime import datetime

from src.core.models import (
    Issue,
    IssueSource,
    ReviewReport,
    ReviewSummary,
    Severity,
    ReviewMode,
    AiAnalysis,
    GitConfig,
    RagConfig,
    ReportConfig,
)


class TestIssue:
    """Tests for Issue model."""

    def test_create_issue(self):
        """Test creating an issue."""
        issue = Issue(
            source=IssueSource.P3C,
            file="UserService.java",
            line=42,
            severity=Severity.WARNING,
            message="类名应该以 Service 结尾",
        )
        
        assert issue.source == IssueSource.P3C
        assert issue.file == "UserService.java"
        assert issue.line == 42
        assert issue.severity == Severity.WARNING
        assert issue.message == "类名应该以 Service 结尾"
        assert issue.id.startswith("issue-")

    def test_issue_get_location(self):
        """Test issue location string."""
        issue = Issue(
            source=IssueSource.AI,
            file="Test.java",
            line=10,
            severity=Severity.INFO,
            message="Test",
        )
        assert issue.get_location() == "Test.java:10"
        
        issue_no_line = Issue(
            source=IssueSource.AI,
            file="Test.java",
            severity=Severity.INFO,
            message="Test",
        )
        assert issue_no_line.get_location() == "Test.java"


class TestReviewReport:
    """Tests for ReviewReport model."""

    def test_create_report(self):
        """Test creating a review report."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.INCREMENTAL,
        )
        
        assert report.repository == "https://github.com/test/repo"
        assert report.mode == ReviewMode.INCREMENTAL
        assert report.summary.total_issues == 0
        assert len(report.issues) == 0

    def test_add_issue(self):
        """Test adding issues to report."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.INCREMENTAL,
        )
        
        issue1 = Issue(
            source=IssueSource.P3C,
            file="Test.java",
            severity=Severity.CRITICAL,
            message="Critical issue",
        )
        issue2 = Issue(
            source=IssueSource.AI,
            file="Test.java",
            severity=Severity.WARNING,
            message="Warning issue",
        )
        
        report.add_issue(issue1)
        report.add_issue(issue2)
        
        assert report.summary.total_issues == 2
        assert report.summary.critical == 1
        assert report.summary.warning == 1

    def test_summary_update(self):
        """Test summary updates correctly."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.FULL,
        )
        
        report.add_issue(Issue(
            source=IssueSource.P3C,
            file="A.java",
            severity=Severity.CRITICAL,
            message="c1",
        ))
        report.add_issue(Issue(
            source=IssueSource.SPOTBUGS,
            file="B.java",
            severity=Severity.CRITICAL,
            message="c2",
        ))
        report.add_issue(Issue(
            source=IssueSource.AI,
            file="C.java",
            severity=Severity.WARNING,
            message="w1",
        ))
        
        assert report.summary.critical == 2
        assert report.summary.warning == 1
        assert report.summary.sources["p3c"] == 1
        assert report.summary.sources["spotbugs"] == 1
        assert report.summary.sources["ai"] == 1


class TestAiAnalysis:
    """Tests for AI analysis."""

    def test_create_analysis(self):
        """Test creating AI analysis."""
        analysis = AiAnalysis(
            is_false_positive=True,
            confidence=0.95,
            reason="This is a false positive because...",
            suggestion="Ignore this issue",
        )
        
        assert analysis.is_false_positive is True
        assert analysis.confidence == 0.95
        assert analysis.reason == "This is a false positive because..."
        assert analysis.suggestion == "Ignore this issue"

    def test_false_positive_tracking(self):
        """Test false positive tracking in report."""
        report = ReviewReport(
            repository="https://github.com/test/repo",
            mode=ReviewMode.INCREMENTAL,
        )
        
        issue = Issue(
            source=IssueSource.SPOTBUGS,
            file="Test.java",
            severity=Severity.WARNING,
            message="Test",
            ai_analysis=AiAnalysis(
                is_false_positive=True,
                confidence=0.9,
            ),
        )
        
        report.add_issue(issue)
        
        assert report.summary.false_positives == 1
        assert report.summary.ai_analyzed == 1


class TestGitConfig:
    """Tests for Git configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GitConfig(
            url="https://github.com/test/repo",
        )
        
        assert config.url == "https://github.com/test/repo"
        assert config.branch == "main"
        assert config.review_mode == ReviewMode.INCREMENTAL

    def test_custom_values(self):
        """Test custom configuration values."""
        config = GitConfig(
            url="https://github.com/test/repo",
            token="test-token",
            branch="develop",
            review_mode=ReviewMode.FULL,
        )
        
        assert config.token == "test-token"
        assert config.branch == "develop"
        assert config.review_mode == ReviewMode.FULL


class TestRagConfig:
    """Tests for RAG configuration."""

    def test_default_values(self):
        """Test default RAG configuration."""
        config = RagConfig()
        
        assert config.enabled is True
        assert config.vector_store_dir == "./vector_store"
        assert config.embedding_model == "text-embedding-ada-002"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100
        assert config.top_k == 5


class TestReportConfig:
    """Tests for Report configuration."""

    def test_default_values(self):
        """Test default report configuration."""
        config = ReportConfig()
        
        assert config.output_format == "json"
        assert config.output_path == "./review_report.json"
        assert config.include_false_positives is True
