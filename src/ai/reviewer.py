"""AI provider and review modules."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from src.core.models import AiAnalysis, AiConfig, Issue, IssueSource, Severity


class AiProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    async def chat(self, prompt: str) -> str:
        """Send chat request and get response."""
        pass
    
    @abstractmethod
    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Send chat request and parse JSON response."""
        pass


class OpenAIProvider(AiProvider):
    """OpenAI API provider."""
    
    def __init__(self, config: AiConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                
                kwargs = {
                    "api_key": self.config.api_key,
                }
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                raise ImportError("Please install openai package")
        
        return self._client
    
    async def chat(self, prompt: str) -> str:
        """Send chat request."""
        client = self._get_client()
        
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        return response.choices[0].message.content
    
    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Send chat request and parse JSON response."""
        full_prompt = f"{prompt}\n\nPlease respond with valid JSON only."
        
        response_text = await self.chat(full_prompt)
        
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {}


class ClaudeProvider(AiProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, config: AiConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """Get or create Claude client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                
                kwargs = {
                    "api_key": self.config.api_key,
                }
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                
                self._client = AsyncAnthropic(**kwargs)
            except ImportError:
                raise ImportError("Please install anthropic package")
        
        return self._client
    
    async def chat(self, prompt: str) -> str:
        """Send chat request."""
        client = self._get_client()
        
        response = await client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        
        return response.content[0].text
    
    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Send chat request and parse JSON response."""
        full_prompt = f"{prompt}\n\nPlease respond with valid JSON only."
        
        response_text = await self.chat(full_prompt)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {}


class AzureOpenAIProvider(AiProvider):
    """Azure OpenAI API provider."""
    
    def __init__(self, config: AiConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """Get or create Azure OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncAzureOpenAI
                
                self._client = AsyncAzureOpenAI(
                    api_key=self.config.api_key,
                    api_version="2024-02-01",
                    azure_endpoint=self.config.base_url or "",
                )
            except ImportError:
                raise ImportError("Please install openai package")
        
        return self._client
    
    async def chat(self, prompt: str) -> str:
        """Send chat request."""
        client = self._get_client()
        
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        return response.choices[0].message.content
    
    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Send chat request and parse JSON response."""
        full_prompt = f"{prompt}\n\nPlease respond with valid JSON only."
        
        response_text = await self.chat(full_prompt)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {}


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek API provider (OpenAI-compatible)."""
    
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(self, config: AiConfig):
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL
        if not config.model:
            config.model = self.DEFAULT_MODEL
        super().__init__(config)


def create_ai_provider(config: AiConfig) -> AiProvider:
    """Create AI provider based on configuration."""
    providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "azure": AzureOpenAIProvider,
        "deepseek": DeepSeekProvider,
    }
    
    provider_class = providers.get(config.provider.lower())
    
    if provider_class is None:
        raise ValueError(f"Unknown AI provider: {config.provider}")
    
    return provider_class(config)


class AiReviewer:
    """AI-powered code reviewer."""
    
    def __init__(self, provider: AiProvider):
        self.provider = provider
    
    async def review_code(
        self,
        code_diff: str,
        relevant_rules: list[str],
    ) -> list[Issue]:
        """Review code using AI with relevant rules."""
        if not relevant_rules:
            prompt = self._build_general_review_prompt(code_diff)
        else:
            prompt = self._build_rule_review_prompt(code_diff, relevant_rules)
        
        try:
            result = await self.provider.chat_json(prompt)
            return self._parse_review_result(result)
        except Exception:
            return []
    
    def _build_general_review_prompt(self, code_diff: str) -> str:
        """Build prompt for general code review."""
        return f"""
Please review the following code changes for issues:

{code_diff}

Please analyze the code for:
1. Potential bugs and logical errors
2. Security vulnerabilities (e.g., SQL injection, XSS, hardcoded secrets)
3. Performance issues
4. Code quality and maintainability
5. Best practices violations

Respond with a JSON array of issues found, where each issue has:
- "file": filename
- "line": line number (if applicable)
- "severity": "CRITICAL", "WARNING", or "INFO"
- "message": brief description
- "description": detailed explanation
- "suggestion": how to fix (if applicable)

If no issues found, return an empty array: []
"""
    
    def _build_rule_review_prompt(self, code_diff: str, relevant_rules: list[str]) -> str:
        """Build prompt for rule-based review."""
        rules_text = "\n".join(f"- {rule}" for rule in relevant_rules)
        
        return f"""
Please review the following code changes against these specific rules:

Relevant Rules:
{rules_text}

Code Changes:
{code_diff}

Please analyze if the code changes comply with the rules above.

Respond with a JSON array of issues found, where each issue has:
- "file": filename
- "line": line number (if applicable)
- "severity": "CRITICAL", "WARNING", or "INFO"
- "message": brief description of the violation
- "description": which rule is violated and why
- "suggestion": how to fix (if applicable)

If no issues found, return an empty array: []
"""
    
    def _parse_review_result(self, result: dict[str, Any]) -> list[Issue]:
        """Parse AI response into Issue objects."""
        issues = []
        
        items = result
        if isinstance(result, dict):
            if "issues" in result:
                items = result["issues"]
            elif "findings" in result:
                items = result["findings"]
        
        if not isinstance(items, list):
            items = [items]
        
        for item in items:
            try:
                severity_str = item.get("severity", "INFO")
                severity = Severity(severity_str.upper())
            except ValueError:
                severity = Severity.INFO
            
            issue = Issue(
                source=IssueSource.AI,
                file=item.get("file", "unknown"),
                line=item.get("line"),
                severity=severity,
                message=item.get("message", ""),
                description=item.get("description"),
                suggestion=item.get("suggestion"),
            )
            issues.append(issue)
        
        return issues


class FalsePositiveAnalyzer:
    """Analyzer for detecting false positives in scan results."""
    
    def __init__(self, provider: AiProvider):
        self.provider = provider
    
    async def analyze_issue(
        self,
        issue: Issue,
        code_context: str,
    ) -> AiAnalysis:
        """Analyze if an issue is a false positive."""
        prompt = self._build_analysis_prompt(issue, code_context)
        
        try:
            result = await self.provider.chat_json(prompt)
            
            is_fp = result.get("is_false_positive", False)
            confidence = result.get("confidence", 0.0)
            reason = result.get("reason")
            suggestion = result.get("suggestion")
            
            if isinstance(is_fp, str):
                is_fp = is_fp.lower() in ("true", "yes", "1")
            
            confidence = max(0.0, min(1.0, float(confidence)))
            
            return AiAnalysis(
                is_false_positive=is_fp,
                confidence=confidence,
                reason=reason,
                suggestion=suggestion,
            )
        except Exception:
            return AiAnalysis(
                is_false_positive=False,
                confidence=0.0,
                reason="Analysis failed",
            )
    
    def _build_analysis_prompt(self, issue: Issue, code_context: str) -> str:
        """Build prompt for false positive analysis."""
        return f"""
Please analyze if the following code issue is a false positive:

Issue Details:
- Source: {issue.source.value}
- Rule ID: {issue.rule_id or "N/A"}
- File: {issue.file}
- Line: {issue.line or "N/A"}
- Severity: {issue.severity.value}
- Message: {issue.message}

Code Context:
{code_context}

Please analyze:
1. Is this a genuine issue or a false positive?
2. Consider the context, is the issue valid in this specific case?

Respond with a JSON object:
- "is_false_positive": true or false
- "confidence": confidence level between 0.0 and 1.0
- "reason": explanation of why it's a false positive or valid issue
- "suggestion": how to fix if it's a valid issue (optional)
"""
    
    async def batch_analyze(
        self,
        issues: list[Issue],
        get_context: callable,
    ) -> list[AiAnalysis]:
        """Analyze multiple issues for false positives."""
        analyses = []
        
        for issue in issues:
            context = get_context(issue)
            analysis = await self.analyze_issue(issue, context)
            analyses.append(analysis)
        
        return analyses
