"""Tests for scanner parsers."""

import os
import tempfile
import pytest
from pathlib import Path

from src.scanner.parser import (
    P3CParser,
    SpotBugsParser,
    CheckstyleParser,
    SonarQubeParser,
    ESLintParser,
    ScannerResultParser,
)
from src.core.models import IssueSource, Severity


class TestP3CParser:
    """Tests for P3C/PMD parser."""

    def test_parse_pmd_xml(self):
        """Test parsing PMD XML report."""
        xml_content = """<?xml version="1.0"?>
<pmd version="6.50.0">
  <file name="UserService.java">
    <violation beginline="10" rule="LawOfDemeter" priority="1">
      类名应该以 Service 结尾
    </violation>
    <violation beginline="20" rule="MissingNullCheck" priority="2">
      方法参数必须进行空值判断
    </violation>
  </file>
</pmd>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            parser = P3CParser()
            issues = parser.parse(temp_path)
            
            assert len(issues) == 2
            assert issues[0].source == IssueSource.P3C
            assert issues[0].file == "UserService.java"
            assert issues[0].line == 10
            assert issues[0].severity == Severity.CRITICAL
            assert "Service" in issues[0].message
        finally:
            os.unlink(temp_path)

    def test_parse_empty_file(self):
        """Test parsing empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            parser = P3CParser()
            issues = parser.parse(temp_path)
            assert len(issues) == 0
        finally:
            os.unlink(temp_path)


class TestSpotBugsParser:
    """Tests for SpotBugs parser."""

    def test_parse_spotbugs_xml(self):
        """Test parsing SpotBugs XML report."""
        xml_content = """<?xml version="1.0"?>
<BugCollection version="5.0.0">
  <BugInstance type="DM_BOOLEAN_CTOR" rank="1" category="STYLE">
    <ShortMessage>new Boolean(...)</ShortMessage>
    <LongMessage>com/example/UserService.java:42: new Boolean(...)</LongMessage>
    <Class name="com.example.UserService"/>
  </BugInstance>
  <BugInstance type="DMI_CONSTANT_DB_PASSWORD" rank="5" category="SECURITY">
    <ShortMessage>Hardcoded database password</ShortMessage>
    <LongMessage>Hardcoded database password</LongMessage>
  </BugInstance>
</BugCollection>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            parser = SpotBugsParser()
            issues = parser.parse(temp_path)
            
            assert len(issues) == 2
            assert issues[0].source == IssueSource.SPOTBUGS
            assert issues[0].rule_id == "DM_BOOLEAN_CTOR"
            assert issues[0].severity == Severity.CRITICAL
        finally:
            os.unlink(temp_path)


class TestCheckstyleParser:
    """Tests for Checkstyle parser."""

    def test_parse_checkstyle_xml(self):
        """Test parsing Checkstyle XML report."""
        xml_content = """<?xml version="1.0"?>
<checkstyle version="10.0">
  <file name="UserService.java">
    <error line="10" column="5" severity="warning" message="Missing a Javadoc comment." source="com.puppycrawl.tools.checkstyle.checks.javadoc.MissingJavadocMethodCheck"/>
    <error line="20" severity="error" message="Line is longer than 120 characters." source="com.puppycrawl.tools.checkstyle.checks.sizes.LineLengthCheck"/>
  </file>
</checkstyle>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            parser = CheckstyleParser()
            issues = parser.parse(temp_path)
            
            assert len(issues) == 2
            assert issues[0].source == IssueSource.CHECKSTYLE
            assert issues[0].file == "UserService.java"
            assert issues[0].line == 10
            assert issues[0].column == 5
        finally:
            os.unlink(temp_path)


class TestSonarQubeParser:
    """Tests for SonarQube parser."""

    def test_parse_sonarqube_json(self):
        """Test parsing SonarQube JSON report."""
        json_content = """{
  "issues": [
    {
      "key": "abc123",
      "rule": "java:S1130",
      "component": "src/UserService.java",
      "line": 42,
      "severity": "MAJOR",
      "message": "This method has 9 parameters, which is greater than the 7 authorized."
    },
    {
      "key": "def456",
      "rule": "java:S1130",
      "component": "src/UserService.java",
      "line": 50,
      "severity": "CRITICAL",
      "message": "This block of commented-out lines of code should be removed."
    }
  ]
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            parser = SonarQubeParser()
            issues = parser.parse(temp_path)
            
            assert len(issues) == 2
            assert issues[0].source == IssueSource.SONARQUBE
            assert issues[0].file == "src/UserService.java"
            assert issues[0].line == 42
            assert issues[0].severity == Severity.WARNING
        finally:
            os.unlink(temp_path)


class TestESLintParser:
    """Tests for ESLint parser."""

    def test_parse_eslint_json(self):
        """Test parsing ESLint JSON report."""
        json_content = """[
  {
    "filePath": "src/index.js",
    "ruleId": "no-unused-vars",
    "severity": 2,
    "line": 10,
    "column": 5,
    "message": "'foo' is defined but never used."
  },
  {
    "filePath": "src/utils.js",
    "ruleId": "no-console",
    "severity": 1,
    "line": 5,
    "message": "Unexpected console statement."
  }
]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            parser = ESLintParser()
            issues = parser.parse(temp_path)
            
            assert len(issues) == 2
            assert issues[0].source == IssueSource.ESLINT
            assert issues[0].file == "src/index.js"
            assert issues[0].line == 10
            assert issues[0].rule_id == "no-unused-vars"
        finally:
            os.unlink(temp_path)


class TestScannerResultParser:
    """Tests for scanner result parser."""

    def test_detect_scanner_by_filename(self):
        """Test scanner type detection by filename."""
        assert ScannerResultParser.detect_scanner("pmd.xml") == "p3c"
        assert ScannerResultParser.detect_scanner("spotbugs.xml") == "spotbugs"
        assert ScannerResultParser.detect_scanner("checkstyle.xml") == "checkstyle"
        assert ScannerResultParser.detect_scanner("sonarqube.json") == "sonarqube"
        assert ScannerResultParser.detect_scanner("eslint.json") == "eslint"

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file."""
        issues = ScannerResultParser.parse_file("/tmp/nonexistent.xml")
        assert len(issues) == 0
