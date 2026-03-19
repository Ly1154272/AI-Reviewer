"""CLI entry point for AI Reviewer."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.ai.reviewer import (
    AiReviewer,
    FalsePositiveAnalyzer,
    create_ai_provider,
)
from src.core.models import (
    AiConfig,
    GitConfig,
    RagConfig,
    ReportConfig,
    ReviewMode,
    ReviewReport,
    ReviewerConfig,
    ScannerConfig,
)
from src.git.client import DiffAnalyzer, GitClient
from src.rag.manager import RAGManager, load_rule_documents
from src.report.generator import ReportGenerator, ResultAggregator
from src.scanner.parser import ScannerResultParser

console = Console()


class Reviewer:
    """Main reviewer orchestrator."""
    
    def __init__(self, config: ReviewerConfig):
        self.config = config
        self.git_client: Optional[GitClient] = None
        self.rag_manager: Optional[RAGManager] = None
        self.ai_reviewer: Optional[AiReviewer] = None
        self.fp_analyzer: Optional[FalsePositiveAnalyzer] = None
    
    async def run(self) -> ReviewReport:
        """Run the review process."""
        report = ReviewReport(
            repository=self.config.git.url,
            branch=self.config.git.branch,
            mode=self.config.git.review_mode,
        )
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task1 = progress.add_task("Cloning repository...", total=None)
                repo_path = self._clone_repo()
                progress.update(task1, completed=True)
                
                task2 = progress.add_task("Parsing scan results...", total=None)
                issues = self._parse_scan_results()
                progress.update(task2, completed=True)
                
                task3 = progress.add_task("Running AI review...", total=None)
                ai_issues = await self._run_ai_review(repo_path)
                issues.extend(ai_issues)
                progress.update(task3, completed=True)
                
                task4 = progress.add_task("Analyzing false positives...", total=None)
                issues = await self._analyze_false_positives(issues, repo_path)
                progress.update(task4, completed=True)
                
                task5 = progress.add_task("Aggregating results...", total=None)
                aggregated = ResultAggregator.aggregate(
                    issues,
                    include_false_positives=self.config.report.include_false_positives,
                )
                progress.update(task5, completed=True)
                
                for issue in aggregated:
                    report.add_issue(issue)
                
                task6 = progress.add_task("Generating report...", total=None)
                self._save_report(report)
                progress.update(task6, completed=True)
        
        finally:
            if self.git_client:
                self.git_client.cleanup()
            if self.rag_manager:
                self.rag_manager.cleanup()
        
        return report
    
    def _clone_repo(self) -> str:
        """Clone repository."""
        self.git_client = GitClient(self.config.git)
        return self.git_client.clone()
    
    def _parse_scan_results(self) -> list:
        """Parse external scan results."""
        if not self.config.scanner.scan_results:
            return []
        
        return ScannerResultParser.parse_files(self.config.scanner.scan_results)
    
    async def _run_ai_review(self, repo_path: str) -> list:
        """Run AI-based review."""
        if not self.git_client:
            return []
        
        changed_files = self.git_client.get_changed_files()
        diffs = DiffAnalyzer.get_code_diffs(self.git_client.repo, changed_files)
        diff_text = DiffAnalyzer.format_diff_for_ai(diffs)
        
        provider = create_ai_provider(self.config.ai)
        self.ai_reviewer = AiReviewer(provider)
        
        if self.config.rag.enabled:
            self.rag_manager = RAGManager(self.config.rag)
            self.rag_manager.initialize()
            
            if self.rag_manager.is_ready():
                relevant_rules = self.rag_manager.retrieve_relevant_rules(diff_text)
            else:
                documents = load_rule_documents(self.config.rule_docs)
                if documents:
                    self.rag_manager.build_index(documents)
                    relevant_rules = self.rag_manager.retrieve_relevant_rules(diff_text)
                else:
                    relevant_rules = []
        else:
            relevant_rules = []
        
        return await self.ai_reviewer.review_code(diff_text, relevant_rules)
    
    async def _analyze_false_positives(self, issues: list, repo_path: str) -> list:
        """Analyze issues for false positives."""
        if not issues:
            return issues
        
        provider = create_ai_provider(self.config.ai)
        self.fp_analyzer = FalsePositiveAnalyzer(provider)
        
        def get_context(issue):
            if not self.git_client:
                return ""
            
            content = self.git_client.get_file_content(issue.file)
            if not content or not issue.line:
                return ""
            
            lines = content.split('\n')
            start = max(0, issue.line - 5)
            end = min(len(lines), issue.line + 5)
            return '\n'.join(lines[start:end])
        
        analyses = await self.fp_analyzer.batch_analyze(issues, get_context)
        
        for issue, analysis in zip(issues, analyses):
            issue.ai_analysis = analysis
        
        return issues
    
    def _save_report(self, report: ReviewReport) -> None:
        """Save review report."""
        generator = ReportGenerator(self.config.report)
        generator.save(report)


def load_config_from_env() -> ReviewerConfig:
    """Load configuration from environment variables."""
    load_dotenv()
    
    git_config = GitConfig(
        url=os.getenv("GIT_URL", ""),
        token=os.getenv("GIT_TOKEN"),
        branch=os.getenv("GIT_BRANCH", "main"),
        review_mode=ReviewMode(
            os.getenv("REVIEW_MODE", "incremental")
        ),
    )
    
    scanner_config = ScannerConfig(
        scan_results=os.getenv("SCAN_RESULTS", "").split(","),
    )
    
    rag_config = RagConfig(
        enabled=os.getenv("RAG_ENABLED", "true").lower() == "true",
        vector_store_dir=os.getenv("VECTOR_STORE_DIR", "./vector_store"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
    )
    
    ai_config = AiConfig(
        provider=os.getenv("AI_PROVIDER", "openai"),
        model=os.getenv("AI_MODEL", "gpt-4"),
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("AI_BASE_URL"),
    )
    
    report_config = ReportConfig(
        output_format=os.getenv("REPORT_FORMAT", "json"),
        output_path=os.getenv("REPORT_OUTPUT", "review_report.json"),
    )
    
    rule_docs = os.getenv("RULE_DOCS", "").split(",")
    rule_docs = [d.strip() for d in rule_docs if d.strip()]
    
    return ReviewerConfig(
        git=git_config,
        scanner=scanner_config,
        rag=rag_config,
        ai=ai_config,
        report=report_config,
        rule_docs=rule_docs,
    )


def load_config_from_yaml(config_path: str) -> ReviewerConfig:
    """Load configuration from YAML file."""
    import yaml
    from pathlib import Path
    
    config_file = Path(config_path)
    if not config_file.exists():
        console.print(f"[yellow]Warning: Config file not found: {config_path}[/yellow]")
        return load_config_from_env()
    
    with open(config_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data:
        return load_config_from_env()
    
    git_data = data.get('git', {})
    git_config = GitConfig(
        url=git_data.get('url', ''),
        token=git_data.get('token'),
        branch=git_data.get('branch', 'main'),
        review_mode=ReviewMode(git_data.get('review_mode', 'incremental')),
    )
    
    scanner_data = data.get('scanner') or {}
    scanner_config = ScannerConfig(
        scan_results=scanner_data.get('scan_results', []),
    )
    
    rag_data = data.get('rag') or {}
    rag_config = RagConfig(
        enabled=rag_data.get('enabled', True),
        vector_store_dir=rag_data.get('vector_store_dir', './vector_store'),
        embedding_model=rag_data.get('embedding_model', 'text-embedding-ada-002'),
        chunk_size=rag_data.get('chunk_size', 1000),
        chunk_overlap=rag_data.get('chunk_overlap', 100),
        top_k=rag_data.get('top_k', 5),
    )
    
    ai_data = data.get('ai') or {}
    ai_config = AiConfig(
        provider=ai_data.get('provider', 'openai'),
        model=ai_data.get('model', 'gpt-4'),
        api_key=ai_data.get('api_key'),
        base_url=ai_data.get('base_url'),
        temperature=ai_data.get('temperature', 0.3),
        max_tokens=ai_data.get('max_tokens', 4096),
    )
    
    report_data = data.get('report') or {}
    report_config = ReportConfig(
        output_format=report_data.get('output_format', 'json'),
        output_path=report_data.get('output_path', 'review_report.json'),
        include_false_positives=report_data.get('include_false_positives', True),
    )
    
    rule_docs = data.get('rule_docs', [])
    if isinstance(rule_docs, str):
        rule_docs = [rule_docs]
    
    return ReviewerConfig(
        git=git_config,
        scanner=scanner_config,
        rag=rag_config,
        ai=ai_config,
        report=report_config,
        rule_docs=rule_docs,
    )


def load_config(config_path: Optional[str] = None) -> ReviewerConfig:
    """Load configuration from YAML file or environment variables."""
    if config_path:
        return load_config_from_yaml(config_path)
    return load_config_from_env()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AI-powered code review system."""
    pass


@cli.command()
@click.option("--config", "-c", help="Configuration file (YAML)")
@click.option("--git-url", "-u", help="Git repository URL")
@click.option("--git-token", "-t", help="Git access token")
@click.option("--branch", "-b", default="main", help="Branch to review")
@click.option("--mode", "-m", type=click.Choice(["full", "incremental"]), default="incremental", help="Review mode")
@click.option("--scan-result", "-s", multiple=True, help="Scan result files (XML/JSON)")
@click.option("--rule-doc", "-r", multiple=True, help="Rule document files")
@click.option("--output", "-o", default="review_report.json", help="Output report path")
@click.option("--format", "-f", type=click.Choice(["json", "html", "markdown"]), default="json", help="Report format")
@click.option("--ai-provider", default="openai", type=click.Choice(["openai", "claude", "azure"]), help="AI provider")
@click.option("--ai-model", default="gpt-4", help="AI model")
@click.option("--ai-api-key", help="AI API key")
@click.option("--no-rag", is_flag=True, help="Disable RAG")
@click.option("--vector-store", default="./vector_store", help="Vector store directory")
def review(
    config: Optional[str],
    git_url: Optional[str],
    git_token: Optional[str],
    branch: str,
    mode: str,
    scan_result,
    rule_doc,
    output: str,
    format: str,
    ai_provider: str,
    ai_model: str,
    ai_api_key: Optional[str],
    no_rag: bool,
    vector_store: str,
):
    """Run code review."""
    config = load_config(config)
    
    if not git_url:
        if not config.git.url:
            console.print("[red]Error: --git-url is required (or set in config file)[/red]")
            sys.exit(1)
    else:
        config.git.url = git_url
        config.git.token = git_token or config.git.token
        config.git.branch = branch
        config.git.review_mode = ReviewMode(mode)
    
    config.scanner.scan_results = list(scan_result) or config.scanner.scan_results
    
    config.rag.enabled = not no_rag
    config.rag.vector_store_dir = vector_store
    
    config.ai.provider = ai_provider
    config.ai.model = ai_model
    if ai_api_key:
        config.ai.api_key = ai_api_key
    
    config.report.output_path = output
    config.report.output_format = format
    
    if rule_doc:
        config.rule_docs = list(rule_doc)
    
    config.ai.api_key = config.ai.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    if not config.ai.api_key:
        console.print("[red]Error: AI API key is required (set --ai-api-key, in config file, or OPENAI_API_KEY/ANTHROPIC_API_KEY env)[/red]")
        sys.exit(1)
    
    reviewer = Reviewer(config)
    
    try:
        report = asyncio.run(reviewer.run())
        
        console.print("\n[green]Review completed![/green]")
        console.print(f"Total issues: {report.summary.total_issues}")
        console.print(f"  Critical: {report.summary.critical}")
        console.print(f"  Warning: {report.summary.warning}")
        console.print(f"  Info: {report.summary.info}")
        console.print(f"  False positives: {report.summary.false_positives}")
        console.print(f"\nReport saved to: {output}")
        
        if report.summary.critical > 0:
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", help="Configuration file (YAML)")
@click.option("--rule-doc", "-r", multiple=True, help="Rule document files (or use config file)")
@click.option("--vector-store", default="./vector_store", help="Vector store directory")
@click.option("--embedding-model", default="text-embedding-ada-002", help="Embedding model")
def build_index(config: Optional[str], rule_doc, vector_store: str, embedding_model: str):
    """Build RAG index from rule documents."""
    import os
    
    from src.rag.manager import RAGManager
    
    cfg = load_config(config)
    
    # Use rule docs from command line or config file
    rule_docs_list = list(rule_doc) if rule_doc else cfg.rule_docs
    
    if not rule_docs_list:
        console.print("[red]Error: --rule-doc is required (or set rule_docs in config file)[/red]")
        sys.exit(1)
    
    api_key = cfg.ai.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY is required (set in config file or environment)[/red]")
        sys.exit(1)
    
    rag_config = RagConfig(
        enabled=True,
        vector_store_dir=vector_store,
        embedding_model=embedding_model or cfg.rag.embedding_model,
    )
    
    manager = RAGManager(rag_config)
    
    try:
        console.print("Loading rule documents...")
        documents = load_rule_documents(rule_docs_list)
        console.print(f"Loaded {len(documents)} documents")
        
        console.print("Building index...")
        manager._init_embeddings()
        manager.build_index(documents)
        
        console.print("[green]Index built successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
