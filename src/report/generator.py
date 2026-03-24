"""Report generation module."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.models import Issue, ReportConfig, ReviewReport, Severity

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generator for review reports."""
    
    def __init__(self, config: ReportConfig):
        self.config = config
    
    def generate(self, report: ReviewReport) -> str:
        """Generate report in configured format."""
        if self.config.output_format == "json":
            return self._generate_json(report)
        elif self.config.output_format == "html":
            return self._generate_html(report)
        elif self.config.output_format == "markdown":
            return self._generate_markdown(report)
        else:
            return self._generate_json(report)
    
    def _generate_json(self, report: ReviewReport) -> str:
        """Generate JSON report."""
        return report.model_dump_json(indent=2)
    
    def _generate_html(self, report: ReviewReport) -> str:
        """Generate HTML report."""
        template_dir = Path(__file__).parent.parent.parent / "templates"
        
        if self.config.template_path:
            template_dir = Path(self.config.template_path).parent
        
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
        )
        
        try:
            template = env.get_template("report.html")
        except Exception as e:
            logger.warning(f"Failed to load template, using default: {e}")
            template = env.from_string(self._get_default_html_template())
        
        critical_issues = [i for i in report.issues if i.severity == Severity.CRITICAL]
        warning_issues = [i for i in report.issues if i.severity == Severity.WARNING]
        info_issues = [i for i in report.issues if i.severity == Severity.INFO]
        
        return template.render(
            report=report,
            critical_issues=critical_issues,
            warning_issues=warning_issues,
            info_issues=info_issues,
        )
    
    def _generate_markdown(self, report: ReviewReport) -> str:
        """Generate Markdown report."""
        lines = []
        
        lines.append(f"# Code Review Report")
        lines.append("")
        lines.append(f"**Repository:** {report.repository}")
        if report.branch:
            lines.append(f"**Branch:** {report.branch}")
        if report.commit_sha:
            lines.append(f"**Commit:** {report.commit_sha}")
        lines.append(f"**Mode:** {report.mode.value}")
        lines.append(f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Issues | {report.summary.total_issues} |")
        lines.append(f"| Critical | {report.summary.critical} |")
        lines.append(f"| Warning | {report.summary.warning} |")
        lines.append(f"| Info | {report.summary.info} |")
        lines.append(f"| False Positives | {report.summary.false_positives} |")
        lines.append(f"| AI Analyzed | {report.summary.ai_analyzed} |")
        lines.append("")
        
        if report.issues:
            lines.append("## Issues")
            lines.append("")
            
            for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
                severity_issues = [i for i in report.issues if i.severity == severity]
                if not severity_issues:
                    continue
                
                lines.append(f"### {severity.value}")
                lines.append("")
                
                for issue in severity_issues:
                    lines.append(f"**{issue.file}**")
                    if issue.line:
                        lines.append(f"- Line {issue.line}")
                    lines.append(f"- {issue.message}")
                    if issue.suggestion:
                        lines.append(f"- Suggestion: {issue.suggestion}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def save(self, report: ReviewReport) -> None:
        """Generate and save report to file."""
        content = self.generate(report)
        
        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _get_default_html_template(self) -> str:
        """Get default HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Review Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .summary-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .summary-card .count { font-size: 2em; font-weight: bold; }
        .summary-card.critical .count { color: #dc3545; }
        .summary-card.warning .count { color: #ffc107; }
        .summary-card.info .count { color: #17a2b8; }
        .issue { background: #fff; border: 1px solid #eee; border-radius: 5px; padding: 15px; margin: 10px 0; }
        .issue.critical { border-left: 4px solid #dc3545; }
        .issue.warning { border-left: 4px solid #ffc107; }
        .issue.info { border-left: 4px solid #17a2b8; }
        .issue-header { font-weight: bold; margin-bottom: 5px; }
        .issue-message { color: #666; }
        .issue-suggestion { background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>Code Review Report</h1>
    
    <p>
        <strong>Repository:</strong> {{ report.repository }}<br>
        {% if report.branch %}<strong>Branch:</strong> {{ report.branch }}<br>{% endif %}
        {% if report.commit_sha %}<strong>Commit:</strong> {{ report.commit_sha[:8] }}<br>{% endif %}
        <strong>Mode:</strong> {{ report.mode.value }}<br>
        <strong>Generated:</strong> {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}
    </p>
    
    <h2>Summary</h2>
    <div class="summary">
        <div class="summary-card">
            <div class="count">{{ report.summary.total_issues }}</div>
            <div>Total</div>
        </div>
        <div class="summary-card critical">
            <div class="count">{{ report.summary.critical }}</div>
            <div>Critical</div>
        </div>
        <div class="summary-card warning">
            <div class="count">{{ report.summary.warning }}</div>
            <div>Warning</div>
        </div>
        <div class="summary-card info">
            <div class="count">{{ report.summary.info }}</div>
            <div>Info</div>
        </div>
    </div>
    
    {% if critical_issues %}
    <h2>Critical Issues ({{ critical_issues|length }})</h2>
    {% for issue in critical_issues %}
    <div class="issue critical">
        <div class="issue-header">{{ issue.file }}{% if issue.line %}:{{ issue.line }}{% endif %}</div>
        <div class="issue-message">{{ issue.message }}</div>
        {% if issue.suggestion %}
        <div class="issue-suggestion"><strong>Suggestion:</strong> {{ issue.suggestion }}</div>
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}
    
    {% if warning_issues %}
    <h2>Warning Issues ({{ warning_issues|length }})</h2>
    {% for issue in warning_issues %}
    <div class="issue warning">
        <div class="issue-header">{{ issue.file }}{% if issue.line %}:{{ issue.line }}{% endif %}</div>
        <div class="issue-message">{{ issue.message }}</div>
        {% if issue.suggestion %}
        <div class="issue-suggestion"><strong>Suggestion:</strong> {{ issue.suggestion }}</div>
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}
    
    {% if info_issues %}
    <h2>Info Issues ({{ info_issues|length }})</h2>
    {% for issue in info_issues %}
    <div class="issue info">
        <div class="issue-header">{{ issue.file }}{% if issue.line %}:{{ issue.line }}{% endif %}</div>
        <div class="issue-message">{{ issue.message }}</div>
        {% if issue.suggestion %}
        <div class="issue-suggestion"><strong>Suggestion:</strong> {{ issue.suggestion }}</div>
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}
</body>
</html>
"""


class ResultAggregator:
    """Aggregator for merging and deduplicating review results."""
    
    @staticmethod
    def aggregate(
        issues: list[Issue],
        include_false_positives: bool = True,
    ) -> list[Issue]:
        """Aggregate and deduplicate issues."""
        unique_issues = ResultAggregator._deduplicate(issues)
        
        if not include_false_positives:
            unique_issues = [
                i for i in unique_issues
                if not (i.ai_analysis and i.ai_analysis.is_false_positive)
            ]
        
        return sorted(
            unique_issues,
            key=lambda x: (
                ResultAggregator._severity_order(x.severity),
                x.file,
                x.line or 0,
            ),
        )
    
    @staticmethod
    def _deduplicate(issues: list[Issue]) -> list[Issue]:
        """Remove duplicate issues."""
        seen = set()
        unique = []
        
        for issue in issues:
            key = (
                issue.file,
                issue.line,
                issue.rule_id,
                issue.message[:50],
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        
        return unique
    
    @staticmethod
    def _severity_order(severity: Severity) -> int:
        """Get order for severity sorting."""
        order = {
            Severity.CRITICAL: 0,
            Severity.WARNING: 1,
            Severity.INFO: 2,
        }
        return order.get(severity, 3)
