"""Core data models for AI Reviewer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class IssueSource(str, Enum):
    """Source of the issue."""
    P3C = "p3c"
    SPOTBUGS = "spotbugs"
    SONARQUBE = "sonarqube"
    CHECKSTYLE = "checkstyle"
    ESLINT = "eslint"
    AI = "ai"
    RAG = "rag"


class ReviewMode(str, Enum):
    """Review mode types."""
    FULL = "full"
    INCREMENTAL = "incremental"


class Issue(BaseModel):
    """Represents a single issue found during review."""
    id: str = Field(default_factory=lambda: Issue.generate_id())
    source: IssueSource
    rule_id: Optional[str] = None
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: Severity
    message: str
    description: Optional[str] = None
    suggestion: Optional[str] = None
    
    ai_analysis: Optional[AiAnalysis] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    
    @staticmethod
    def generate_id() -> str:
        """Generate unique ID for issue."""
        import uuid
        return f"issue-{uuid.uuid4().hex[:8]}"
    
    def get_location(self) -> str:
        """Get issue location string."""
        if self.line:
            return f"{self.file}:{self.line}"
        return self.file


class AiAnalysis(BaseModel):
    """AI analysis result for an issue."""
    is_false_positive: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    relevant_rules: Optional[list[str]] = None


class ReviewSummary(BaseModel):
    """Summary of review results."""
    total_issues: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0
    false_positives: int = 0
    ai_analyzed: int = 0
    sources: dict[str, int] = Field(default_factory=dict)


class ReviewReport(BaseModel):
    """Complete review report."""
    id: str = Field(default_factory=lambda: ReviewReport.generate_id())
    repository: str
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    mode: ReviewMode
    summary: ReviewSummary = Field(default_factory=ReviewSummary)
    issues: list[Issue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    
    @staticmethod
    def generate_id() -> str:
        """Generate unique ID for report."""
        import uuid
        return f"report-{uuid.uuid4().hex[:8]}"
    
    def add_issue(self, issue: Issue) -> None:
        """Add issue to report and update summary."""
        self.issues.append(issue)
        self._update_summary(issue)
    
    def _update_summary(self, issue: Issue) -> None:
        """Update summary counts."""
        self.summary.total_issues += 1
        
        severity_count = getattr(self.summary, issue.severity.name.lower())
        setattr(self.summary, issue.severity.name.lower(), severity_count + 1)
        
        if issue.ai_analysis and issue.ai_analysis.is_false_positive:
            self.summary.false_positives += 1
        
        if issue.ai_analysis:
            self.summary.ai_analyzed += 1
        
        source = issue.source.value
        self.summary.sources[source] = self.summary.sources.get(source, 0) + 1


class CodeDiff(BaseModel):
    """Represents code changes."""
    file_path: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff: Optional[str] = None
    status: str = "modified"


class GitConfig(BaseModel):
    """Git repository configuration."""
    url: str
    token: Optional[str] = None
    branch: str = "main"
    review_mode: ReviewMode = ReviewMode.INCREMENTAL
    
    pr_number: Optional[int] = None
    base_commit: Optional[str] = None
    head_commit: Optional[str] = None


class ScannerConfig(BaseModel):
    """Scanner configuration."""
    scan_results: list[str] = Field(default_factory=list)
    enabled_scanners: list[str] = Field(default_factory=list)


class RagConfig(BaseModel):
    """RAG configuration."""
    enabled: bool = True
    vector_store_dir: str = "./vector_store"
    embedding_model: str = "text-embedding-ada-002"
    local_model_path: Optional[str] = None  # 内网环境下使用本地模型路径
    chunk_size: int = 1000
    chunk_overlap: int = 100
    top_k: int = 5


class AiConfig(BaseModel):
    """AI provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096


class ReportConfig(BaseModel):
    """Report configuration."""
    output_format: str = "json"
    output_path: str = "./review_report.json"
    include_false_positives: bool = True
    template_path: Optional[str] = None


class ReviewerConfig(BaseModel):
    """Main configuration for AI Reviewer."""
    git: GitConfig
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    
    rule_docs: list[str] = Field(default_factory=list)
