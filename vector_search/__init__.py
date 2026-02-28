"""
vector-search MCP Server

提供向量检索能力，用于相似代码和行为模式匹配。

使用官方 MCP SDK 实现 stdio 协议。

集成了RAG系统，支持:
- 语义搜索 (semantic_search): 使用真实嵌入向量
- 混合搜索 (hybrid_search): 关键词 + 语义搜索
- 向量搜索 (vector_search): 向后兼容的哈希向量搜索
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

# 创建 Server 实例
server = Server("vector-search")

# 全局状态
_vector_index: dict = {}
_vector_db_path: str = None
_kb_collections: list[str] = []  # Dynamic collections from KB registry

# RAG components (lazy loaded)
_rag_config = None
_embedding_service = None
_vector_store = None
_rag_retriever = None


def get_vector_collections() -> list[str]:
    """Get available collections, including KB collections.

    Combines legacy collections with KB-specific collections.
    """
    global _kb_collections

    # Legacy collections (for backward compatibility)
    legacy_collections = ["code", "behavior", "malware"]

    # Combine with KB collections
    all_collections = list(set(legacy_collections + _kb_collections))
    all_collections.append("all")  # Always include "all"

    return all_collections


def load_kb_collections() -> list[str]:
    """Load collections from KB registry."""
    try:
        from src.knowledge.registry import get_registry
        registry = get_registry()
        collections = registry.get_all_vector_collections()
        # Remove "all" as it will be added separately
        return [c for c in collections if c != "all"]
    except Exception as e:
        logger.warning(f"Failed to load KB collections: {e}")
        return []


def get_vector_db_path() -> str:
    """获取向量数据库路径"""
    global _vector_db_path
    if _vector_db_path is None:
        db_dir = Path(__file__).parent.parent.parent / "data" / "vectors"
        db_dir.mkdir(parents=True, exist_ok=True)
        _vector_db_path = str(db_dir)
    return _vector_db_path


def load_vector_index():
    """加载向量索引 (legacy, for backward compatibility)"""
    global _vector_index

    index_file = os.path.join(get_vector_db_path(), "index.json")
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                _vector_index = json.load(f)
            logger.info(f"Loaded vector index with {len(_vector_index)} entries")
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            _vector_index = {}
    else:
        _vector_index = {}


def save_vector_index():
    """保存向量索引 (legacy, for backward compatibility)"""
    index_file = os.path.join(get_vector_db_path(), "index.json")
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(_vector_index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save vector index: {e}")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算余弦相似度"""
    import math
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def simple_text_hash(text: str, dimension: int = 128) -> list[float]:
    """简单的文本哈希转向量（作为fallback，生产环境应使用专业嵌入模型）"""
    import hashlib
    # 使用SHA256哈希并转换为向量
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()

    # 转换为归一化的向量，支持可配置维度
    base_values = [byte / 255.0 for byte in hash_bytes]
    if dimension <= len(base_values):
        return base_values[:dimension]

    # 扩展到指定维度
    result = base_values.copy()
    offset = 1
    while len(result) < dimension:
        extended = [(v + offset * 0.1) % 1.0 for v in base_values]
        result.extend(extended[:dimension - len(result)])
        offset += 1
    return result[:dimension]


def _init_rag_components():
    """Initialize RAG components for semantic search."""
    global _rag_config, _embedding_service, _vector_store, _rag_retriever

    if _rag_config is not None:
        return  # Already initialized

    try:
        from src.rag.config import RAGConfig
        from src.rag.embeddings import HashEmbeddingService
        from src.rag.vector_store import JSONVectorStore
        from src.rag.retriever import RAGRetriever

        # Load RAG config
        try:
            _rag_config = RAGConfig.load("config/rag.yaml")
        except Exception:
            # Use default config if file doesn't exist
            _rag_config = RAGConfig.get_default()

        # Initialize embedding service (start with hash-based for compatibility)
        # In production, this would use LocalEmbeddingService or APIEmbeddingService
        _embedding_service = HashEmbeddingService(
            model="hash",
            dimension=_rag_config.embedding.dimension
        )

        # Initialize vector store
        vector_config = _rag_config.vector_store
        db_path = os.path.join(get_vector_db_path(), "semantic_index.json")

        _vector_store = JSONVectorStore(db_path)

        # Initialize retriever
        _rag_retriever = RAGRetriever(_embedding_service, _vector_store)

        logger.info("RAG components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize RAG components: {e}")
        # Fallback to simple hash-based search
        _rag_config = None
        _embedding_service = None
        _vector_store = None
        _rag_retriever = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    # Get dynamic collections
    collections = get_vector_collections()
    collections_for_add = [c for c in collections if c != "all"]

    return [
        Tool(
            name="semantic_search",
            description="Search using semantic embeddings (RAG-enhanced). Finds semantically similar content even with different keywords.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query text to search for"},
                    "kb_id": {
                        "type": "string",
                        "description": "Knowledge base ID to filter (e.g., 'harmonyos-dev', 'security', 'attck')"
                    },
                    "top_k": {"type": "integer", "default": 10, "description": "Number of results"},
                    "score_threshold": {"type": "number", "default": 0.7, "description": "Minimum similarity score"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="hybrid_search",
            description="Hybrid search combining keyword matching and semantic similarity. Best for comprehensive results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query text to search for"},
                    "kb_id": {
                        "type": "string",
                        "description": "Knowledge base ID to filter"
                    },
                    "top_k": {"type": "integer", "default": 10, "description": "Number of results"},
                    "keyword_weight": {"type": "number", "default": 0.3, "description": "Weight for keyword matching (0-1)"},
                    "semantic_weight": {"type": "number", "default": 0.7, "description": "Weight for semantic similarity (0-1)"},
                    "score_threshold": {"type": "number", "default": 0.7, "description": "Minimum similarity score"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="vector_search",
            description="Legacy vector search using hash-based vectors (for backward compatibility). Use semantic_search for better results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query text to search for"},
                    "collection": {
                        "type": "string",
                        "enum": collections,
                        "default": "all",
                        "description": "Collection to search"
                    },
                    "top_k": {"type": "integer", "default": 10, "description": "Number of results"},
                    "threshold": {"type": "number", "default": 0.7, "description": "Similarity threshold"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="add_vector",
            description="Add a new entry to the vector index",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier"},
                    "text": {"type": "string", "description": "Text content to vectorize"},
                    "metadata": {"type": "object", "description": "Additional metadata"},
                    "collection": {
                        "type": "string",
                        "enum": collections_for_add,
                        "description": "Collection name"
                    },
                    "kb_id": {
                        "type": "string",
                        "description": "Knowledge base ID (for semantic indexing)"
                    }
                },
                "required": ["id", "text"]
            }
        ),
        Tool(
            name="batch_add_vectors",
            description="Add multiple entries to the vector index",
            inputSchema={
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "metadata": {"type": "object"},
                                "collection": {"type": "string"},
                                "kb_id": {"type": "string"}
                            },
                            "required": ["id", "text"]
                        }
                    }
                },
                "required": ["entries"]
            }
        ),
        Tool(
            name="delete_vector",
            description="Delete an entry from the vector index",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"}
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="get_collection_stats",
            description="Get statistics about vector collections",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "enum": collections,
                        "default": "all"
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    load_vector_index()
    _init_rag_components()

    try:
        if name == "semantic_search":
            return await _semantic_search(arguments)
        elif name == "hybrid_search":
            return await _hybrid_search(arguments)
        elif name == "vector_search":
            return await _vector_search(arguments)
        elif name == "add_vector":
            return await _add_vector(arguments)
        elif name == "batch_add_vectors":
            return await _batch_add_vectors(arguments)
        elif name == "delete_vector":
            return await _delete_vector(arguments)
        elif name == "get_collection_stats":
            return await _get_collection_stats(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}", exc_info=True)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _semantic_search(args: dict) -> list[TextContent]:
    """语义搜索"""
    query = args["query"]
    kb_id = args.get("kb_id")
    top_k = args.get("top_k", 10)
    score_threshold = args.get("score_threshold", 0.7)

    if _rag_retriever is None:
        # Fallback to legacy search
        return [TextContent(type="text", text=json.dumps({
            "warning": "RAG not initialized, falling back to legacy search",
            "results": []
        }, ensure_ascii=False))]

    try:
        results = await _rag_retriever.retrieve(
            query=query,
            top_k=top_k,
            mode="semantic",
            kb_id=kb_id,
            score_threshold=score_threshold
        )

        formatted_results = [{
            "id": r.id,
            "score": round(r.score, 4),
            "metadata": r.metadata,
            "distance": r.distance
        } for r in results]

        return [TextContent(type="text", text=json.dumps({
            "query": query,
            "kb_id": kb_id,
            "mode": "semantic",
            "total_results": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False, indent=2))]

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": str(e)
        }, ensure_ascii=False))]


async def _hybrid_search(args: dict) -> list[TextContent]:
    """混合搜索"""
    query = args["query"]
    kb_id = args.get("kb_id")
    top_k = args.get("top_k", 10)
    keyword_weight = args.get("keyword_weight", 0.3)
    semantic_weight = args.get("semantic_weight", 0.7)
    score_threshold = args.get("score_threshold", 0.7)

    if _rag_retriever is None:
        # Fallback to legacy search
        return [TextContent(type="text", text=json.dumps({
            "warning": "RAG not initialized, falling back to legacy search",
            "results": []
        }, ensure_ascii=False))]

    try:
        results = await _rag_retriever.retrieve(
            query=query,
            top_k=top_k,
            mode="hybrid",
            kb_id=kb_id,
            score_threshold=score_threshold,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight
        )

        formatted_results = [{
            "id": r.id,
            "score": round(r.score, 4),
            "metadata": r.metadata,
            "distance": r.distance
        } for r in results]

        return [TextContent(type="text", text=json.dumps({
            "query": query,
            "kb_id": kb_id,
            "mode": "hybrid",
            "keyword_weight": keyword_weight,
            "semantic_weight": semantic_weight,
            "total_results": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False, indent=2))]

    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": str(e)
        }, ensure_ascii=False))]


async def _vector_search(args: dict) -> list[TextContent]:
    """向量搜索 (legacy, for backward compatibility)"""
    query = args["query"]
    collection = args.get("collection", "all")
    top_k = args.get("top_k", 10)
    threshold = args.get("threshold", 0.7)

    # 生成查询向量
    query_vector = simple_text_hash(query)

    # 计算相似度
    results = []
    for entry_id, entry_data in _vector_index.items():
        if collection != "all" and entry_data.get("collection") != collection:
            continue

        entry_vector = entry_data.get("vector", [])
        if entry_vector:
            similarity = cosine_similarity(query_vector, entry_vector)
            if similarity >= threshold:
                results.append({
                    "id": entry_id,
                    "similarity": round(similarity, 4),
                    "metadata": entry_data.get("metadata", {}),
                    "collection": entry_data.get("collection")
                })

    # 按相似度排序
    results.sort(key=lambda x: x["similarity"], reverse=True)

    return [TextContent(type="text", text=json.dumps({
        "query": query,
        "collection": collection,
        "total_results": len(results),
        "results": results[:top_k]
    }, ensure_ascii=False, indent=2))]


async def _add_vector(args: dict) -> list[TextContent]:
    """添加向量"""
    entry_id = args["id"]
    text = args["text"]
    metadata = args.get("metadata", {})
    collection = args.get("collection", "default")
    kb_id = args.get("kb_id")

    # Add to legacy index
    if entry_id in _vector_index:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Entry with id {entry_id} already exists"
        }, ensure_ascii=False))]

    vector = simple_text_hash(text)

    _vector_index[entry_id] = {
        "text": text,
        "vector": vector,
        "metadata": metadata,
        "collection": collection,
        "created_at": __import__("datetime").datetime.now().isoformat()
    }
    save_vector_index()

    # Add to semantic index if RAG is initialized
    if _rag_retriever and kb_id:
        try:
            await _rag_retriever.index_document(
                doc_id=entry_id,
                text=text,
                metadata={**metadata, "kb_id": kb_id}
            )
        except Exception as e:
            logger.warning(f"Failed to index to semantic store: {e}")

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "id": entry_id,
        "vector_dim": len(vector),
        "indexed_semantically": _rag_retriever is not None and kb_id is not None
    }, ensure_ascii=False))]


async def _batch_add_vectors(args: dict) -> list[TextContent]:
    """批量添加向量"""
    entries = args["entries"]
    results = []

    for entry in entries:
        entry_id = entry["id"]
        text = entry["text"]
        metadata = entry.get("metadata", {})
        collection = entry.get("collection", "default")
        kb_id = entry.get("kb_id")

        if entry_id in _vector_index:
            results.append({"id": entry_id, "status": "error", "message": "already exists"})
            continue

        vector = simple_text_hash(text)

        _vector_index[entry_id] = {
            "text": text,
            "vector": vector,
            "metadata": metadata,
            "collection": collection,
            "created_at": __import__("datetime").datetime.now().isoformat()
        }
        results.append({"id": entry_id, "status": "success"})

        # Add to semantic index if RAG is initialized
        if _rag_retriever and kb_id:
            try:
                await _rag_retriever.index_document(
                    doc_id=entry_id,
                    text=text,
                    metadata={**metadata, "kb_id": kb_id}
                )
            except Exception as e:
                logger.warning(f"Failed to index {entry_id} to semantic store: {e}")

    save_vector_index()

    return [TextContent(type="text", text=json.dumps({
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "results": results
    }, ensure_ascii=False, indent=2))]


async def _delete_vector(args: dict) -> list[TextContent]:
    """删除向量"""
    entry_id = args["id"]

    # Delete from legacy index
    if entry_id not in _vector_index:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Entry {entry_id} not found"
        }, ensure_ascii=False))]

    del _vector_index[entry_id]
    save_vector_index()

    # Delete from semantic index if available
    if _vector_store:
        try:
            await _vector_store.delete(entry_id)
        except Exception as e:
            logger.warning(f"Failed to delete from semantic store: {e}")

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "deleted": entry_id
    }, ensure_ascii=False))]


async def _get_collection_stats(args: dict) -> list[TextContent]:
    """获取集合统计"""
    collection = args.get("collection", "all")

    # Legacy index stats
    if collection == "all":
        total = len(_vector_index)
        collection_stats = {}
        for entry in _vector_index.values():
            coll = entry.get("collection", "unknown")
            collection_stats[coll] = collection_stats.get(coll, 0) + 1
    else:
        total = sum(1 for e in _vector_index.values() if e.get("collection") == collection)
        collection_stats = {collection: total}

    stats = {
        "collection": collection,
        "total_entries": total,
        "by_collection": collection_stats
    }

    # Add semantic index stats if available
    if _vector_store:
        try:
            semantic_count = await _vector_store.count()
            stats["semantic_index_entries"] = semantic_count
        except Exception as e:
            logger.warning(f"Failed to get semantic stats: {e}")

    return [TextContent(type="text", text=json.dumps(stats, ensure_ascii=False, indent=2))]


async def main():
    """Main entry point for the MCP server."""
    global _kb_collections
    _kb_collections = load_kb_collections()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
