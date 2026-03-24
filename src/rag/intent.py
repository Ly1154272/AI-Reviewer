"""Code intent extraction using AST parsing."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


class CodeIntentExtractor:
    """Extract natural language intent from code using AST."""
    
    SUPPORTED_EXTENSIONS = {
        ".py": "python",
    }
    
    def __init__(self):
        self._intent_cache = {}
    
    def extract(self, file_path: str, source_code: str) -> str:
        """Extract intent from source code.
        
        Args:
            file_path: Path to the source file
            source_code: Source code content
            
        Returns:
            Natural language description of code intent
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == ".py":
            return self._extract_python_intent(source_code)
        
        return source_code
    
    def _extract_python_intent(self, source_code: str) -> str:
        """Extract intent from Python code using AST."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return source_code
        
        intents = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                intent = self._extract_function_intent(node)
                if intent:
                    intents.append(intent)
            elif isinstance(node, ast.ClassDef):
                intent = self._extract_class_intent(node)
                if intent:
                    intents.append(intent)
            elif isinstance(node, ast.Assign):
                intent = self._extract_assignment_intent(node)
                if intent:
                    intents.append(intent)
        
        if not intents:
            return source_code
        
        return "; ".join(intents)
    
    def _extract_function_intent(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract function intent."""
        parts = []
        
        name = node.name
        parts.append(f"function '{name}'")
        
        if node.args.args:
            params = [arg.arg for arg in node.args.args[:3]]
            parts.append(f"params: {', '.join(params)}")
        
        returns = self._get_return_type(node)
        if returns:
            parts.append(f"returns: {returns}")
        
        calls = self._extract_function_calls(node)
        if calls:
            parts.append(f"calls: {', '.join(calls)}")
        
        return f"Function {name}: {', '.join(parts)}" if parts else None
    
    def _extract_class_intent(self, node: ast.ClassDef) -> Optional[str]:
        """Extract class intent."""
        base_classes = [base.attr if isinstance(base, ast.Attribute) else base.id if isinstance(base, ast.Name) else str(base) 
                       for base in node.bases]
        
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        
        parts = [f"class '{node.name}'"]
        if base_classes:
            parts.append(f"extends: {', '.join(base_classes)}")
        if methods:
            parts.append(f"methods: {', '.join(methods[:5])}")
        
        return ", ".join(parts)
    
    def _extract_assignment_intent(self, node: ast.Assign) -> Optional[str]:
        """Extract assignment intent."""
        targets = [t.id if isinstance(t, ast.Name) else self._extract_value_str(t) 
                   for t in node.targets]
        
        value_desc = self._extract_value_str(node.value)
        
        if targets and value_desc:
            return f"variable {targets[0]} = {value_desc}"
        
        return None
    
    def _get_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation."""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
        return None
    
    def _extract_function_calls(self, node: ast.FunctionDef) -> list[str]:
        """Extract function calls within a function."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))[:5]
    
    def _extract_value_str(self, node: ast.AST) -> str:
        """Extract string representation of a node."""
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            
            args = []
            for arg in node.args[:2]:
                args.append(self._extract_value_str(arg))
            
            return f"{func_name}({', '.join(args)})" if args else func_name
        
        elif isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, str) and len(val) > 20:
                return f"'{val[:20]}...'"
            return f"'{val}'" if isinstance(val, str) else str(val)
        
        elif isinstance(node, ast.BinOp):
            return f"binary_op({node.op.__class__.__name__})"
        
        elif isinstance(node, ast.Dict):
            keys = [str(k.value) if isinstance(k, ast.Constant) else '?' for k in node.keys[:3]]
            return f"dict(keys: {', '.join(keys)})"
        
        elif isinstance(node, ast.List):
            return f"list(len={len(node.elts)})"
        
        elif isinstance(node, ast.Name):
            return node.id
        
        elif isinstance(node, ast.Attribute):
            return node.attr
        
        return "..."


def extract_code_intent(file_path: str, source_code: str) -> str:
    """Convenience function to extract code intent.
    
    Args:
        file_path: Path to the source file
        source_code: Source code content
        
    Returns:
        Natural language description of code intent
    """
    extractor = CodeIntentExtractor()
    return extractor.extract(file_path, source_code)
