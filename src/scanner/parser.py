"""Scanner result parsers for various tools."""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.core.models import Issue, IssueSource, Severity

logger = logging.getLogger(__name__)


class IssueParser(ABC):
    """Abstract base class for issue parsers."""
    
    @abstractmethod
    def parse(self, file_path: str) -> list[Issue]:
        """Parse scan result file and return list of issues."""
        pass
    
    @staticmethod
    def _map_severity(severity: str) -> Severity:
        """Map tool-specific severity to standard severity."""
        severity_map = {
            "error": Severity.CRITICAL,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
            "high": Severity.CRITICAL,
            "medium": Severity.WARNING,
            "low": Severity.INFO,
            "critical": Severity.CRITICAL,
            "blocker": Severity.CRITICAL,
            "major": Severity.WARNING,
            "minor": Severity.INFO,
            "1": Severity.CRITICAL,
            "2": Severity.CRITICAL,
            "3": Severity.CRITICAL,
            "4": Severity.CRITICAL,
            "5": Severity.WARNING,
            "6": Severity.WARNING,
            "7": Severity.WARNING,
            "8": Severity.WARNING,
            "9": Severity.WARNING,
            "10": Severity.INFO,
            "11": Severity.INFO,
            "12": Severity.INFO,
            "13": Severity.INFO,
            "14": Severity.INFO,
            "15": Severity.INFO,
            "16": Severity.INFO,
            "17": Severity.INFO,
            "18": Severity.INFO,
            "19": Severity.INFO,
            "20": Severity.INFO,
        }
        
        if severity.lower() in severity_map:
            return severity_map[severity.lower()]
        
        try:
            rank = int(severity)
            if rank <= 4:
                return Severity.CRITICAL
            elif rank <= 9:
                return Severity.WARNING
            else:
                return Severity.INFO
        except (ValueError, TypeError):
            return Severity.INFO


class P3CParser(IssueParser):
    """Parser for P3C (Alibaba Java Coding Guidelines) PMD results."""
    
    SOURCE = IssueSource.P3C
    
    def parse(self, file_path: str) -> list[Issue]:
        """Parse PMD XML report."""
        issues = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for file_elem in root.findall(".//file"):
                filename = file_elem.get("name", "")
                
                for violation in file_elem.findall("violation"):
                    issue = Issue(
                        source=self.SOURCE,
                        rule_id=violation.get("rule"),
                        file=filename,
                        line=int(violation.get("beginline", 0)),
                        severity=self._map_severity(violation.get("priority", "Warning")),
                        message=(violation.text or "").strip(),
                    )
                    issues.append(issue)
                
        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
        except Exception as e:
            logger.error(f"Failed to parse P3C results: {e}")
        
        return issues


class SpotBugsParser(IssueParser):
    """Parser for SpotBugs results."""
    
    SOURCE = IssueSource.SPOTBUGS
    
    def parse(self, file_path: str) -> list[Issue]:
        """Parse SpotBugs XML report."""
        issues = []
        
        try:
            if file_path.endswith('.json'):
                return self._parse_json(file_path)
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for bug_instance in root.findall(".//BugInstance"):
                issue = Issue(
                    source=self.SOURCE,
                    rule_id=bug_instance.get("type", ""),
                    file=bug_instance.get("class", ""),
                    line=int(bug_instance.get("line", 0)) if bug_instance.get("line") else None,
                    severity=self._map_severity(bug_instance.get("rank", "Warning")),
                    message=bug_instance.findtext("ShortMessage") or bug_instance.findtext("LongMessage") or "",
                    description=bug_instance.findtext("LongMessage"),
                )
                issues.append(issue)
                
        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
        except Exception as e:
            logger.error(f"Failed to parse SpotBugs XML results: {e}")
        
        return issues
    
    def _parse_json(self, file_path: str) -> list[Issue]:
        """Parse SpotBugs JSON report."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for bug in data.get("bugs", {}).get("bug", []):
                issue = Issue(
                    source=self.SOURCE,
                    rule_id=bug.get("type", ""),
                    file=bug.get("class", {}).get("$", ""),
                    line=bug.get("lineNumber"),
                    severity=self._map_severity(bug.get("rank", "Warning")),
                    message=bug.get("shortMessage", ""),
                    description=bug.get("longMessage", ""),
                )
                issues.append(issue)
                
        except Exception as e:
            logger.error(f"Failed to parse SpotBugs JSON results: {e}")
        
        return issues


class CheckstyleParser(IssueParser):
    """Parser for Checkstyle results."""
    
    SOURCE = IssueSource.CHECKSTYLE
    
    def parse(self, file_path: str) -> list[Issue]:
        """Parse Checkstyle XML report."""
        issues = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for file_elem in root.findall(".//file"):
                filename = file_elem.get("name", "")
                
                for error in file_elem.findall("error"):
                    issue = Issue(
                        source=self.SOURCE,
                        rule_id=error.get("source", ""),
                        file=filename,
                        line=int(error.get("line", 0)) if error.get("line") else None,
                        column=int(error.get("column", 0)) if error.get("column") else None,
                        severity=self._map_severity(error.get("severity", "warning")),
                        message=error.get("message", ""),
                    )
                    issues.append(issue)
                    
        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Checkstyle results: {e}")
        
        return issues


class SonarQubeParser(IssueParser):
    """Parser for SonarQube results."""
    
    SOURCE = IssueSource.SONARQUBE
    
    def parse(self, file_path: str) -> list[Issue]:
        """Parse SonarQube JSON report."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for issue_data in data.get("issues", []):
                issue = Issue(
                    source=self.SOURCE,
                    rule_id=issue_data.get("rule", ""),
                    file=issue_data.get("component", ""),
                    line=issue_data.get("line"),
                    severity=self._map_severity(issue_data.get("severity", "MAJOR")),
                    message=issue_data.get("message", ""),
                    description=issue_data.get("description"),
                )
                issues.append(issue)
                
        except Exception as e:
            logger.error(f"Failed to parse SonarQube results: {e}")
        
        return issues


class ESLintParser(IssueParser):
    """Parser for ESLint results."""
    
    SOURCE = IssueSource.ESLINT
    
    def parse(self, file_path: str) -> list[Issue]:
        """Parse ESLint JSON report."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    severity = item.get("severity")
                    if isinstance(severity, int):
                        severity = "warning" if severity >= 1 else "info"
                    else:
                        severity = str(severity)
                    
                    issue = Issue(
                        source=self.SOURCE,
                        rule_id=item.get("ruleId", ""),
                        file=item.get("filePath", ""),
                        line=item.get("line"),
                        column=item.get("column"),
                        severity=self._map_severity(severity),
                        message=item.get("message", ""),
                    )
                    issues.append(issue)
                    
        except Exception as e:
            logger.error(f"Failed to parse ESLint results: {e}")
        
        return issues


class ScannerResultParser:
    """Main parser for scanner results."""
    
    _parsers = {
        "p3c": P3CParser,
        "pmd": P3CParser,
        "spotbugs": SpotBugsParser,
        "checkstyle": CheckstyleParser,
        "sonarqube": SonarQubeParser,
        "eslint": ESLintParser,
    }
    
    @classmethod
    def detect_scanner(cls, file_path: str) -> Optional[str]:
        """Detect scanner type from file path."""
        path = Path(file_path).name.lower()
        
        if "pmd" in path or "p3c" in path:
            return "p3c"
        if "spotbugs" in path or "findbugs" in path:
            return "spotbugs"
        if "checkstyle" in path:
            return "checkstyle"
        if "sonarqube" in path or "sonar" in path:
            return "sonarqube"
        if "eslint" in path:
            return "eslint"
        
        ext = Path(file_path).suffix.lower()
        if ext == '.xml':
            return "p3c"
        if ext == '.json':
            return "eslint"
        
        return None
    
    @classmethod
    def parse_file(cls, file_path: str) -> list[Issue]:
        """Parse a single scan result file."""
        scanner_type = cls.detect_scanner(file_path)
        
        if scanner_type and scanner_type in cls._parsers:
            parser = cls._parsers[scanner_type]()
            return parser.parse(file_path)
        
        for parser_cls in cls._parsers.values():
            parser = parser_cls()
            issues = parser.parse(file_path)
            if issues:
                return issues
        
        return []
    
    @classmethod
    def parse_files(cls, file_paths: list[str]) -> list[Issue]:
        """Parse multiple scan result files."""
        all_issues = []
        
        for file_path in file_paths:
            if not Path(file_path).exists():
                continue
            
            issues = cls.parse_file(file_path)
            all_issues.extend(issues)
        
        return all_issues
