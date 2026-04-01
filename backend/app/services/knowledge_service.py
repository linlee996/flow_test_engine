"""知识库核心服务 - 文档分块、向量化、ChromaDB 操作、检索"""
import re
import logging

import chromadb
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.document_parser import DocumentParser

logger = logging.getLogger(__name__)
settings = get_settings()

# 分块配置
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Markdown 表格正则：匹配完整的 markdown 表格（表头 + 分隔行 + 数据行）
_TABLE_PATTERN = re.compile(
    r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)',
    re.MULTILINE,
)


class KnowledgeBaseService:
    """知识库核心服务 - 管理 ChromaDB 中的文档向量"""

    def __init__(self):
        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        self._parser = DocumentParser()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    @staticmethod
    def _collection_name(project_id: int) -> str:
        """项目对应的 collection 名称"""
        return f"project_{project_id}"

    def _get_or_create_collection(self, project_id: int) -> chromadb.Collection:
        """获取或创建项目 collection"""
        return self._client.get_or_create_collection(
            name=self._collection_name(project_id),
            metadata={"hnsw:space": "cosine"},
        )

    def _split_with_table_awareness(self, markdown_content: str) -> list[str]:
        """
        表格感知的文本分块：保证 markdown 表格不被从中间劈开。

        策略：
        1. 用正则提取所有 markdown 表格块
        2. 用占位符替换原文中的表格
        3. 对非表格文本用 RecursiveCharacterTextSplitter 正常分块
        4. 每个表格作为独立 chunk（超大表格按行拆分，每个子块保留表头）
        5. 按原始顺序合并文本 chunks 和表格 chunks
        """
        # 提取所有表格及其位置
        tables: list[dict] = []
        placeholder_template = "\n\n__TABLE_PLACEHOLDER_{idx}__\n\n"

        def _replace_table(match: re.Match) -> str:
            idx = len(tables)
            tables.append({
                "content": match.group(1).strip(),
                "start": match.start(),
            })
            return placeholder_template.format(idx=idx)

        # 替换表格为占位符
        text_without_tables = _TABLE_PATTERN.sub(_replace_table, markdown_content)

        # 对非表格文本正常分块
        text_chunks = self._splitter.split_text(text_without_tables) if text_without_tables.strip() else []

        # 处理表格 chunks
        table_chunks: dict[int, list[str]] = {}
        for idx, table_info in enumerate(tables):
            table_text = table_info["content"]
            if len(table_text) <= CHUNK_SIZE:
                # 表格够小，整体作为一个 chunk
                table_chunks[idx] = [table_text]
            else:
                # 表格太大，按行拆分并保留表头
                table_chunks[idx] = self._split_large_table(table_text)

        # 按原始顺序合并：遍历 text_chunks，遇到占位符则替换为对应的表格 chunks
        final_chunks: list[str] = []
        placeholder_re = re.compile(r'__TABLE_PLACEHOLDER_(\d+)__')

        for chunk in text_chunks:
            matches = list(placeholder_re.finditer(chunk))
            if not matches:
                # 纯文本 chunk，直接加入
                cleaned = chunk.strip()
                if cleaned:
                    final_chunks.append(cleaned)
            else:
                # chunk 中包含表格占位符
                # 先提取占位符前后的文本
                last_end = 0
                for m in matches:
                    # 占位符前的文本
                    before_text = chunk[last_end:m.start()].strip()
                    if before_text:
                        final_chunks.append(before_text)
                    # 插入表格 chunks
                    table_idx = int(m.group(1))
                    if table_idx in table_chunks:
                        final_chunks.extend(table_chunks[table_idx])
                        del table_chunks[table_idx]  # 标记已处理
                    last_end = m.end()
                # 占位符后的文本
                after_text = chunk[last_end:].strip()
                if after_text:
                    final_chunks.append(after_text)

        # 处理可能未被 text_chunks 包含的剩余表格（边界情况）
        for idx in sorted(table_chunks.keys()):
            final_chunks.extend(table_chunks[idx])

        return final_chunks if final_chunks else self._splitter.split_text(markdown_content)

    @staticmethod
    def _split_large_table(table_text: str) -> list[str]:
        """
        拆分超大 markdown 表格：按行拆分，每个子块保留表头和分隔行。
        """
        lines = table_text.strip().split('\n')
        if len(lines) < 3:
            return [table_text]

        header_line = lines[0]
        separator_line = lines[1]
        data_lines = lines[2:]
        header_block = f"{header_line}\n{separator_line}"
        header_len = len(header_block)

        chunks: list[str] = []
        current_lines: list[str] = []
        current_len = header_len

        for line in data_lines:
            line_len = len(line) + 1  # +1 for newline
            if current_len + line_len > CHUNK_SIZE and current_lines:
                # 当前块已满，保存并开始新块
                chunk_text = header_block + "\n" + "\n".join(current_lines)
                chunks.append(chunk_text)
                current_lines = []
                current_len = header_len

            current_lines.append(line)
            current_len += line_len

        # 最后一个块
        if current_lines:
            chunk_text = header_block + "\n" + "\n".join(current_lines)
            chunks.append(chunk_text)

        return chunks if chunks else [table_text]

    def add_document(
        self,
        project_id: int,
        file_path: str,
        doc_id: int,
        filename: str,
        embeddings: Embeddings,
    ) -> int:
        """
        解析文档 -> 分块 -> 向量化 -> 存入 ChromaDB
        返回分块数量（同步方法，需在线程池中调用）
        """
        # 1. Parse document - skip image extraction for knowledge base (text-only for vector search)
        parsed_doc = self._parser.parse(file_path, extract_images=False)
        markdown_content = parsed_doc.markdown

        if not markdown_content.strip():
            raise ValueError("文档内容为空，无法创建知识库条目")

        # 2. 表格感知的文本分块
        chunks = self._split_with_table_awareness(markdown_content)
        if not chunks:
            raise ValueError("文档分块结果为空")

        # 3. 批量生成 Embedding
        chunk_embeddings = embeddings.embed_documents(chunks)

        # 4. 存入 ChromaDB
        collection = self._get_or_create_collection(project_id)

        ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_id": doc_id,
                "filename": filename,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            embeddings=chunk_embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        logger.info(f"Document {doc_id} added to project {project_id}: {len(chunks)} chunks")
        return len(chunks)

    def remove_document(self, project_id: int, doc_id: int) -> None:
        """从 ChromaDB 删除指定文档的所有 chunks"""
        try:
            collection = self._client.get_collection(
                name=self._collection_name(project_id)
            )
            # 按 document_id 元数据过滤删除
            collection.delete(where={"document_id": doc_id})
            logger.info(f"Document {doc_id} removed from project {project_id}")
        except ValueError:
            # collection 不存在，跳过
            logger.warning(f"Collection for project {project_id} not found, skip delete")

    def delete_collection(self, project_id: int) -> None:
        """删除整个项目的 collection"""
        try:
            self._client.delete_collection(name=self._collection_name(project_id))
            logger.info(f"Collection for project {project_id} deleted")
        except ValueError:
            logger.warning(f"Collection for project {project_id} not found, skip delete")

    def search(
        self,
        project_id: int,
        query: str,
        embeddings: Embeddings,
        top_k: int = 5,
    ) -> list[dict]:
        """
        检索相关文档片段
        返回 [{"content": str, "metadata": dict, "distance": float}]
        """
        try:
            collection = self._client.get_collection(
                name=self._collection_name(project_id)
            )
        except ValueError:
            logger.warning(f"Collection for project {project_id} not found")
            return []

        # 检查 collection 是否为空
        if collection.count() == 0:
            return []

        # 实际返回数量不能超过 collection 中的文档数
        actual_top_k = min(top_k, collection.count())

        # 生成查询向量
        query_embedding = embeddings.embed_query(query)

        # 检索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 格式化结果
        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return search_results

    def get_collection_stats(self, project_id: int) -> dict:
        """获取项目 collection 的统计信息"""
        try:
            collection = self._client.get_collection(
                name=self._collection_name(project_id)
            )
            return {"count": collection.count()}
        except ValueError:
            return {"count": 0}
