"""Semantic search using vector database."""

import os
from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.config import Settings

from agent.models import SearchResult
from agent.tools.embeddings import EmbeddingManager


class SemanticSearch:
    """Semantic search using ChromaDB vector database."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        workspace_path: str,
        persist_directory: str = "./data/chroma",
    ):
        """
        Initialize semantic search.

        Args:
            embedding_manager: Manager for generating embeddings
            workspace_path: Path to the workspace/codebase
            persist_directory: Directory to persist ChromaDB
        """
        self.embedding_manager = embedding_manager
        self.workspace_path = Path(workspace_path)
        self.persist_directory = persist_directory

        # Initialize ChromaDB
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(
                name="codebase",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"Warning: ChromaDB collection error: {e}")
            self.collection = None

    async def index_codebase(
        self, file_extensions: Optional[List[str]] = None
    ) -> int:
        """
        Index the codebase into the vector database.

        Args:
            file_extensions: List of file extensions to index (e.g., ['.py', '.js'])

        Returns:
            Number of chunks indexed
        """
        if not self.collection:
            print("Warning: ChromaDB collection not available")
            return 0

        if file_extensions is None:
            file_extensions = [
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".java",
                ".cpp",
                ".c",
                ".go",
                ".rs",
                ".rb",
                ".php",
            ]

        # Collect files
        files_to_index = []
        for ext in file_extensions:
            files_to_index.extend(self.workspace_path.rglob(f"*{ext}"))

        # Filter out common directories to skip
        skip_dirs = {"node_modules", ".git", "__pycache__", "venv", "env", "dist", "build"}
        files_to_index = [
            f
            for f in files_to_index
            if not any(skip_dir in f.parts for skip_dir in skip_dirs)
        ]

        print(f"Indexing {len(files_to_index)} files...")

        chunks = []
        metadatas = []
        ids = []
        chunk_id = 0

        for file_path in files_to_index:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Simple chunking strategy: split by function/class or by lines
                file_chunks = self._chunk_code(content)

                for chunk in file_chunks:
                    if len(chunk.strip()) < 50:  # Skip very small chunks
                        continue

                    chunks.append(chunk)
                    metadatas.append(
                        {
                            "file_path": str(file_path.relative_to(self.workspace_path)),
                            "full_path": str(file_path),
                        }
                    )
                    ids.append(f"chunk_{chunk_id}")
                    chunk_id += 1

            except Exception as e:
                print(f"Warning: Failed to index {file_path}: {e}")

        if not chunks:
            print("No chunks to index")
            return 0

        # Generate embeddings
        print(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = await self.embedding_manager.embed_texts(chunks)

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            try:
                self.collection.add(
                    documents=chunks[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    metadatas=metadatas[i:batch_end],
                    ids=ids[i:batch_end],
                )
            except Exception as e:
                print(f"Warning: Failed to add batch to ChromaDB: {e}")

        print(f"Indexed {len(chunks)} code chunks")
        return len(chunks)

    def _chunk_code(self, content: str, max_chunk_size: int = 500) -> List[str]:
        """
        Chunk code content.

        Args:
            content: Code content
            max_chunk_size: Maximum chunk size in lines

        Returns:
            List of code chunks
        """
        lines = content.split("\n")
        chunks = []
        current_chunk = []

        for line in lines:
            current_chunk.append(line)

            # Split on function/class definitions or when chunk gets too large
            if (
                line.strip().startswith(("def ", "class ", "function ", "export "))
                or len(current_chunk) >= max_chunk_size
            ):
                if len(current_chunk) > 5:  # Minimum chunk size
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []

        # Add remaining lines
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    async def search(
        self, query: str, max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search the codebase semantically.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        if not self.collection:
            print("Warning: ChromaDB collection not available")
            return []

        try:
            # Generate query embedding
            query_embedding = await self.embedding_manager.embed_single(query)

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=max_results
            )

            # Convert to SearchResult objects
            search_results = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    # Convert distance to similarity score (0-1)
                    similarity = 1 - distance

                    search_results.append(
                        SearchResult(
                            source=metadata.get("file_path", "unknown"),
                            content=doc,
                            relevance_score=similarity,
                            metadata={
                                "search_type": "semantic",
                                "full_path": metadata.get("full_path", ""),
                            },
                        )
                    )

            return search_results

        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return []

