"""Docling 文档解析服务 - 把需求文档解析成 markdown + 多模态内容"""
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode


@dataclass
class ParsedDocument:
    """解析后的文档"""
    markdown: str  # 文档的 markdown 内容
    images: list[dict]  # 图片列表 [{"caption": str, "base64": str}]
    tables: list[dict]  # 表格列表 [{"caption": str, "markdown": str}]


class DocumentParser:
    """Docling 文档解析器"""

    def __init__(self):
        self.converter = DocumentConverter()

    def parse(self, file_path: str, advanced_parsing: bool = True) -> ParsedDocument:
        """
        解析文档，提取 markdown 内容和多模态元素
        支持 PDF、DOCX、DOC、TXT 等格式
        
        Args:
            file_path: 文档路径
            advanced_parsing: 是否启用高级解析（OCR 识别图片/表格），默认 True
        """
        result = self.converter.convert(file_path)
        doc = result.document

        # 导出为 markdown
        markdown_content = doc.export_to_markdown()

        images = []
        tables = []
        
        # 仅在启用高级解析时提取图片和表格
        if advanced_parsing:
            # 提取图片（base64编码）
            for idx, picture in enumerate(doc.pictures):
                try:
                    img_data = {
                        "caption": getattr(picture, "caption", f"图片{idx + 1}"),
                        "base64": self._extract_image_base64(picture),
                    }
                    if img_data["base64"]:
                        images.append(img_data)
                except Exception:
                    pass  # 跳过无法提取的图片

            # 提取表格
            for idx, table in enumerate(doc.tables):
                try:
                    df = table.export_to_dataframe()
                    tables.append({
                        "caption": getattr(table, "caption", f"表格{idx + 1}"),
                        "markdown": df.to_markdown(index=False),
                    })
                except Exception:
                    pass  # 跳过无法提取的表格

        return ParsedDocument(
            markdown=markdown_content,
            images=images,
            tables=tables,
        )

    def _extract_image_base64(self, picture) -> Optional[str]:
        """提取图片的 base64 编码"""
        if hasattr(picture, "image") and picture.image:
            img_bytes = picture.image.tobytes() if hasattr(picture.image, "tobytes") else None
            if img_bytes:
                return base64.b64encode(img_bytes).decode("utf-8")
        return None
