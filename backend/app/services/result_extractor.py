"""结果提取服务 - 从 Agent 输出中提取 Excel 和总结"""
import re
import os
from pathlib import Path
from typing import Optional
import pandas as pd
from app.core.config import get_settings

settings = get_settings()


class ResultExtractor:
    """从 markdown 报告中提取结果"""

    def __init__(self):
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_and_save(self, report_markdown: str, task_id: int, filename: str) -> tuple[str, str, str]:
        """
        从 markdown 报告中提取表格和总结
        返回: (excel_path, summary_path, full_markdown_path)
        """
        # 保存完整的 Agent 输出
        full_markdown_path = self._save_full_markdown(report_markdown, task_id)

        # 提取最后一个 markdown 表格
        excel_path = self._extract_table_to_excel(report_markdown, task_id, filename)

        # 提取总结内容
        summary_path = self._extract_summary(report_markdown, task_id)

        return excel_path, summary_path, full_markdown_path

    def _save_full_markdown(self, markdown: str, task_id: int) -> str:
        """保存完整的 Agent 输出到文件"""
        full_markdown_filename = f"{task_id}_full_output.md"
        full_markdown_path = self.output_dir / full_markdown_filename

        with open(full_markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return str(full_markdown_path)

    def _extract_table_to_excel(self, markdown: str, task_id: int, filename: str) -> str:
        """提取最后一个 markdown 表格并保存为 Excel"""
        # 匹配 markdown 表格
        table_pattern = r'\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+'
        tables = re.findall(table_pattern, markdown)

        if not tables:
            raise ValueError("报告中未找到测试用例表格")

        # 取最后一个表格
        last_table = tables[-1]

        # 解析表格为 DataFrame
        df = self._parse_markdown_table(last_table)

        # 保存为 Excel
        safe_filename = self._sanitize_filename(filename)
        excel_filename = f"{task_id}_{safe_filename}.xlsx"
        excel_path = self.output_dir / excel_filename

        df.to_excel(excel_path, index=False, engine="openpyxl")

        return str(excel_path)

    def _clean_cell_content(self, content: str) -> str:
        """清理单元格内容中的 HTML 标签和实体，转换为 Excel 友好格式"""
        if not content:
            return content

        # 将 <br>、<br/>、<br /> 转换为换行符
        result = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)

        # 处理常见的 HTML 实体
        html_entities = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
            '&#39;': "'",
            '&mdash;': '—',
            '&ndash;': '–',
            '&hellip;': '…',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™',
        }
        for entity, char in html_entities.items():
            result = result.replace(entity, char)

        # 处理数字型 HTML 实体，如 &#160; &#x20; 等
        result = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), result)
        result = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), result)

        # 移除其他残留的 HTML 标签（如 <p>、<span> 等）
        result = re.sub(r'<[^>]+>', '', result)

        # 清理多余的空白字符（但保留换行符）
        result = re.sub(r'[ \t]+', ' ', result)  # 多个空格/制表符合并为一个空格
        result = re.sub(r'\n{3,}', '\n\n', result)  # 多个换行符合并为两个

        return result.strip()

    def _parse_markdown_table(self, table_str: str) -> pd.DataFrame:
        """解析 markdown 表格为 DataFrame"""
        lines = [line.strip() for line in table_str.strip().split('\n') if line.strip()]

        if len(lines) < 2:
            raise ValueError("表格格式不正确")

        # 解析表头
        header_line = lines[0]
        headers = [self._clean_cell_content(cell.strip()) for cell in header_line.split('|') if cell.strip()]

        # 跳过分隔行，解析数据行
        data_rows = []
        for line in lines[2:]:  # 跳过表头和分隔行
            cells = [self._clean_cell_content(cell.strip()) for cell in line.split('|') if cell.strip()]
            if cells:
                # 确保列数匹配
                while len(cells) < len(headers):
                    cells.append("")
                data_rows.append(cells[:len(headers)])

        return pd.DataFrame(data_rows, columns=headers)

    def _extract_summary(self, markdown: str, task_id: int) -> str:
        """提取总结内容并保存为 md 文件"""
        summary_content = ""

        # 匹配"测试覆盖度总结"标题及其后的所有内容（不限标题级别）
        patterns = [
            # 匹配包含"测试覆盖度总结"的标题，提取到文件结尾
            r'(#+\s*测试覆盖度总结[\s\S]*)',
            # 匹配包含"步骤4"的标题，提取到文件结尾
            r'(#+\s*.*步骤\s*4[\s\S]*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE | re.MULTILINE)
            if match:
                summary_content = match.group(1).strip()
                break

        # 如果没找到步骤4，尝试提取最后一个markdown标题段落
        if not summary_content:
            last_section_pattern = r'(#+\s*[^\n]+\n[\s\S]+?)(?=\n#+\s*[^\n]+\n|$)'
            matches = list(re.finditer(last_section_pattern, markdown))
            if matches:
                # 取最后一个非表格段落
                for match in reversed(matches):
                    content = match.group(1).strip()
                    if '|' not in content[:100]:  # 避免提取表格
                        summary_content = content
                        break

        # 如果还是没找到，取表格之前的所有内容
        if not summary_content:
            table_match = re.search(r'\|[^\n]+\|', markdown)
            if table_match:
                summary_content = markdown[:table_match.start()].strip()
            else:
                summary_content = markdown[:1000]  # 取前1000字符

        # 保存总结文件
        summary_filename = f"{task_id}_summary.md"
        summary_path = self.output_dir / summary_filename

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)

        return str(summary_path)

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不安全字符"""
        # 移除扩展名
        name = Path(filename).stem
        # 替换不安全字符
        unsafe_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(unsafe_chars, '_', name)
        return safe_name[:50]  # 限制长度

    def read_summary(self, summary_path: str) -> Optional[str]:
        """读取总结文件内容"""
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
