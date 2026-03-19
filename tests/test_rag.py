"""Tests for RAG module."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.rag.manager import (
    RAGManager,
    load_rule_documents,
    _load_single_file,
    _load_text_file,
)
from src.core.models import RagConfig


class TestLoadRuleDocuments:
    """Tests for load_rule_documents function."""

    def test_load_markdown_file(self):
        """Test loading markdown file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Rules\n\n## Naming\n- Class names should end with Service")
            temp_path = f.name
        
        try:
            docs = load_rule_documents([temp_path])
            assert len(docs) == 1
            assert "Test Rules" in docs[0]
        finally:
            os.unlink(temp_path)

    def test_load_text_file(self):
        """Test loading text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test rule document.")
            temp_path = f.name
        
        try:
            docs = load_rule_documents([temp_path])
            assert len(docs) == 1
            assert "test rule" in docs[0]
        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        docs = load_rule_documents(["/tmp/nonexistent.md"])
        assert len(docs) == 0

    def test_load_directory(self):
        """Test loading directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file1 = Path(tmpdir) / "rules1.md"
            md_file2 = Path(tmpdir) / "rules2.md"
            
            md_file1.write_text("# Rules 1\n- Rule A")
            md_file2.write_text("# Rules 2\n- Rule B")
            
            docs = load_rule_documents([tmpdir])
            assert len(docs) == 2

    def test_mixed_files_and_directories(self):
        """Test mixing files and directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "single.md"
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            file2 = subdir / "nested.md"
            
            file1.write_text("# Single Rule")
            file2.write_text("# Nested Rule")
            
            docs = load_rule_documents([str(file1), str(subdir)])
            assert len(docs) == 2


class TestLoadTextFile:
    """Tests for _load_text_file function."""

    def test_load_utf8_file(self):
        """Test loading UTF-8 file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("测试文档内容")
            temp_path = f.name
        
        try:
            content = _load_text_file(Path(temp_path))
            assert content == "测试文档内容"
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Test loading empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            content = _load_text_file(Path(temp_path))
            assert content is None
        finally:
            os.unlink(temp_path)


class TestRAGManager:
    """Tests for RAGManager."""

    def test_init(self):
        """Test RAGManager initialization."""
        config = RagConfig(
            enabled=True,
            vector_store_dir="./test_vector_store",
            embedding_model="text-embedding-ada-002",
        )
        
        manager = RAGManager(config, api_key="test-key")
        
        assert manager.config.enabled is True
        assert manager.config.vector_store_dir == "./test_vector_store"
        assert manager.api_key == "test-key"

    @patch('src.rag.manager.RAGManager._init_embeddings')
    def test_initialize_disabled(self, mock_init):
        """Test initialization when disabled."""
        config = RagConfig(enabled=False)
        manager = RAGManager(config)
        manager.initialize()
        
        mock_init.assert_not_called()

    @patch('langchain_openai.OpenAIEmbeddings')
    def test_init_embeddings_with_api_key(self, mock_embeddings):
        """Test initializing embeddings with API key."""
        config = RagConfig(
            enabled=True,
            embedding_model="text-embedding-ada-002",
        )
        manager = RAGManager(config, api_key="test-key")
        manager._init_embeddings()
        
        mock_embeddings.assert_called_once()
        call_kwargs = mock_embeddings.call_args[1]
        assert call_kwargs["model"] == "text-embedding-ada-002"
        assert call_kwargs["api_key"] == "test-key"

    @patch('langchain_openai.OpenAIEmbeddings')
    def test_init_embeddings_without_api_key(self, mock_embeddings):
        """Test initializing embeddings without API key."""
        config = RagConfig(
            enabled=True,
            embedding_model="text-embedding-ada-002",
        )
        manager = RAGManager(config, api_key=None)
        manager._init_embeddings()
        
        mock_embeddings.assert_called_once()
        call_kwargs = mock_embeddings.call_args[1]
        assert call_kwargs["model"] == "text-embedding-ada-002"
        assert "api_key" not in call_kwargs

    def test_is_ready(self):
        """Test is_ready method."""
        config = RagConfig(enabled=False)
        manager = RAGManager(config)
        
        assert manager.is_ready() is False
        
        config.enabled = True
        manager._vector_store = MagicMock()
        assert manager.is_ready() is True

    def test_cleanup(self):
        """Test cleanup method."""
        config = RagConfig()
        manager = RAGManager(config)
        
        manager._vector_store = MagicMock()
        manager._embeddings = MagicMock()
        
        manager.cleanup()
        
        assert manager._vector_store is None
        assert manager._embeddings is None
