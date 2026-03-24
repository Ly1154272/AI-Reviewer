"""Git client for code review system."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import git
from git import Repo

from src.core.models import CodeDiff, GitConfig, ReviewMode

logger = logging.getLogger(__name__)


class GitClient:
    """Git client for interacting with repositories."""
    
    def __init__(self, config: GitConfig):
        self.config = config
        self._repo: Optional[Repo] = None
        self._temp_dir: Optional[str] = None
    
    def setup(self) -> str:
        """Setup repository (clone from URL or use local path)."""
        if self.config.local_path:
            return self._setup_local()
        return self.clone()
    
    def _setup_local(self) -> str:
        """Use local repository path."""
        local_path = Path(self.config.local_path).resolve()
        
        if not local_path.exists():
            raise ValueError(f"Local path does not exist: {local_path}")
        
        if not (local_path / ".git").exists():
            raise ValueError(f"Local path is not a git repository: {local_path}")
        
        self._repo = Repo(local_path)
        self._temp_dir = str(local_path)
        logger.info(f"Using local repository: {local_path}")
        return str(local_path)
    
    def clone(self) -> str:
        """Clone repository to temporary directory."""
        import os
        import git
        
        clone_url = self._get_clone_url()
        self._temp_dir = tempfile.mkdtemp(prefix="ai-reviewer-")
        
        env = os.environ.copy()
        env["GIT_TIMEOUT"] = "600"
        
        self._repo = Repo.clone_from(
            clone_url,
            self._temp_dir,
            branch=self.config.branch,
            env=env,
        )
        return self._temp_dir
    
    def _get_clone_url(self) -> str:
        """Get clone URL with authentication."""
        if self.config.token:
            if "github.com" in self.config.url:
                return self.config.url.replace(
                    "https://",
                    f"https://oauth2:{self.config.token}@"
                )
            elif "gitlab.com" in self.config.url:
                return self.config.url.replace(
                    "https://",
                    f"https://oauth2:{self.config.token}@"
                )
        return self.config.url
    
    @property
    def repo(self) -> Repo:
        """Get repository instance."""
        if self._repo is None:
            raise RuntimeError("Repository not cloned. Call clone() first.")
        return self._repo
    
    def get_changed_files(self, base: Optional[str] = None, head: Optional[str] = None) -> list[str]:
        """Get list of changed files."""
        if self.config.review_mode == ReviewMode.INCREMENTAL:
            return self._get_incremental_changes(base, head)
        return self._get_all_files()
    
    def _get_incremental_changes(self, base: Optional[str], head: Optional[str]) -> list[str]:
        """Get incremental changes between base and head commits."""
        try:
            if base and head:
                commit_range = f"{base}...{head}"
                diff_index = self.repo.index.diff(commit_range)
            elif self.config.pr_number:
                diff_index = self.repo.index.diff("HEAD~1")
            else:
                diff_index = self.repo.index.diff("HEAD")
            
            changed_files = []
            for diff in diff_index:
                if diff.a_path:
                    changed_files.append(diff.a_path)
                if diff.b_path:
                    changed_files.append(diff.b_path)
            
            return list(set(changed_files))
        except Exception as e:
            logger.warning(f"Failed to get incremental changes: {e}")
            return self._get_untracked_and_staged()
    
    def _get_untracked_and_staged(self) -> list[str]:
        """Get untracked and staged files."""
        files = []
        
        for item in self.repo.index.diff("HEAD"):
            if item.b_path:
                files.append(item.b_path)
        
        for item in self.repo.untracked_files:
            files.append(item)
        
        return files
    
    def _get_all_files(self) -> list[str]:
        """Get all files in repository."""
        files = []
        for root, _, filenames in os.walk(self._temp_dir):
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                filepath = os.path.relpath(
                    os.path.join(root, filename),
                    self._temp_dir
                )
                files.append(filepath)
        return files
    
    def get_file_content(self, file_path: str, commit: Optional[str] = None) -> Optional[str]:
        """Get file content at specific commit or current."""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        try:
            if commit:
                blob = self.repo.commit(commit).tree[file_path]
                return blob.data_stream.read().decode('utf-8')
            
            full_path = os.path.join(self._temp_dir, file_path)
            if os.path.exists(full_path):
                for encoding in encodings:
                    try:
                        with open(full_path, 'r', encoding=encoding) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
                logger.warning(f"Failed to decode file {file_path} with any encoding")
        except KeyError as e:
            logger.warning(f"KeyError when getting file content: {e}")
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
        return None
    
    def get_diff(self, file_path: str) -> Optional[str]:
        """Get diff for specific file."""
        try:
            diff = self.repo.index.diff(None, paths=[file_path])
            if diff:
                return str(diff[0])
            
            diff = self.repo.index.diff("HEAD", paths=[file_path])
            if diff:
                return str(diff[0])
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
        return None
    
    def get_current_commit(self) -> str:
        """Get current commit SHA."""
        return self.repo.head.commit.hexsha
    
    def get_branch_name(self) -> str:
        """Get current branch name."""
        return self.repo.active_branch.name
    
    def cleanup(self) -> None:
        """Clean up temporary directory."""
        import shutil
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)


class DiffAnalyzer:
    """Analyzer for code differences."""
    
    @staticmethod
    def get_code_diffs(repo: Repo, files: list[str]) -> list[CodeDiff]:
        """Get code diffs for specified files."""
        diffs = []
        
        for file_path in files:
            try:
                diff_entry = repo.index.diff(None, paths=[file_path])
                if not diff_entry:
                    diff_entry = repo.index.diff("HEAD", paths=[file_path])
                
                if diff_entry:
                    diff = diff_entry[0]
                    code_diff = CodeDiff(
                        file_path=file_path,
                        diff=str(diff),
                        status=DiffAnalyzer._get_status(diff),
                    )
                    diffs.append(code_diff)
                else:
                    blob = repo.head.commit.tree[file_path]
                    code_diff = CodeDiff(
                        file_path=file_path,
                        new_content=blob.data_stream.read().decode('utf-8'),
                        status="added",
                    )
                    diffs.append(code_diff)
            except KeyError:
                code_diff = CodeDiff(
                    file_path=file_path,
                    status="added",
                )
                diffs.append(code_diff)
            except Exception as e:
                logger.warning(f"Failed to get diff for {file_path}: {e}")
                code_diff = CodeDiff(
                    file_path=file_path,
                    status="unknown",
                )
                diffs.append(code_diff)
        
        return diffs
    
    @staticmethod
    def _get_status(diff) -> str:
        """Get diff status."""
        if diff.new_file:
            return "added"
        if diff.deleted_file:
            return "deleted"
        if diff.renamed:
            return "renamed"
        return "modified"
    
    @staticmethod
    def format_diff_for_ai(diffs: list[CodeDiff]) -> str:
        """Format diffs for AI analysis."""
        output = []
        for diff in diffs:
            output.append(f"\n{'='*60}")
            output.append(f"File: {diff.file_path}")
            output.append(f"Status: {diff.status}")
            output.append(f"{'='*60}\n")
            
            if diff.diff:
                output.append(diff.diff)
            elif diff.new_content:
                output.append("--- New Content ---")
                output.append(diff.new_content)
        
        return "\n".join(output)
