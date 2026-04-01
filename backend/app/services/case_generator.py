"""LangGraph 用例生成工作流 - 4 阶段渐进式 Prompt + 人机澄清循环"""
import uuid
from pathlib import Path
from typing import TypedDict, Annotated, Optional, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from app.core.config import get_settings
from app.services.document_parser import ParsedDocument

settings = get_settings()

# Prompt 文件目录
PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"
# 兼容：保留旧的单文件 prompt 路径
LEGACY_PROMPT_FILE = Path(__file__).parent.parent.parent / "config" / "prompt.md"


def load_phase_prompt(phase: str) -> str:
    """
    加载指定阶段的 prompt，自动拼接 role.md + 阶段 prompt。

    Args:
        phase: 阶段名称，如 'phase1_analysis', 'phase2_strategy' 等
    """
    role_file = PROMPTS_DIR / "role.md"
    phase_file = PROMPTS_DIR / f"{phase}.md"

    if not role_file.exists():
        raise FileNotFoundError(f"Role prompt not found: {role_file}")
    if not phase_file.exists():
        raise FileNotFoundError(f"Phase prompt not found: {phase_file}")

    role_text = role_file.read_text(encoding="utf-8")
    phase_text = phase_file.read_text(encoding="utf-8")

    return f"{role_text}\n\n---\n\n{phase_text}"


def load_legacy_prompt() -> str:
    """加载旧的完整 prompt.md（兼容用途）"""
    if LEGACY_PROMPT_FILE.exists():
        return LEGACY_PROMPT_FILE.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Legacy prompt file not found: {LEGACY_PROMPT_FILE}")


def create_llm(provider: str, api_key: str, base_url: str, model: str) -> BaseChatModel:
    """
    根据厂商创建对应的 LLM 实例

    - OpenAI/DeepSeek/Kimi: 使用 ChatOpenAI（OpenAI 兼容 API）
    - Gemini: 使用 ChatGoogleGenerativeAI
    - Anthropic: 使用 ChatAnthropic
    """
    provider = provider.lower() if provider else "openai"

    # OpenAI 兼容的厂商（OpenAI、DeepSeek、Kimi）
    if provider in ("openai", "deepseek", "kimi"):
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=f"{base_url.rstrip('/')}/v1" if base_url else None,
        )

    # Gemini - 使用 Google 的 LangChain 集成
    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
            )
        except ImportError:
            # 如果没有安装 langchain-google-genai，回退到 OpenAI 兼容模式
            return ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=f"{base_url.rstrip('/')}/v1beta/openai",
            )

    # Anthropic
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model,
                api_key=api_key,
            )
        except ImportError:
            raise ImportError("请安装 langchain-anthropic: pip install langchain-anthropic")

    # 默认使用 OpenAI 兼容
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=f"{base_url.rstrip('/')}/v1" if base_url else None,
    )


class WorkflowState(TypedDict):
    """工作流状态"""
    messages: Annotated[list, add_messages]
    document_content: str  # 解析后的文档 markdown
    images: list[dict]  # 多模态图片 [{"caption": str, "base64": str}]
    tables: list[dict]  # 表格内容
    system_prompt: str  # 自定义模板 prompt（仅用于 phase3 输出格式覆盖，可为空）
    current_step: str  # 当前执行步骤
    has_clarification: bool  # 是否有待澄清问题
    clarification_questions: str  # 待澄清问题
    report_markdown: str  # 最终输出的 markdown 报告（各阶段拼接）
    is_stopped: bool  # 用户是否停止生成
    rag_context: str  # RAG 检索到的项目知识库上下文（可为空）
    # 各阶段的中间结果
    analysis_result: str  # Phase1 输出：结构分析 + 需求分析 + 对称性检查
    strategy_result: str  # Phase2 输出：测试策略 + 闭环验证 + 自检清单
    cases_markdown: str  # Phase3 输出：测试用例表格
    summary_result: str  # Phase4 输出：覆盖度总结


class CaseGeneratorWorkflow:
    """用例生成工作流 - 4 阶段渐进式 Prompt"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        provider: str = "openai",
        on_step: Optional[Callable[[str], None]] = None,
    ):
        self.llm = create_llm(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        self.on_step = on_step
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        构建 4 阶段 LangGraph 工作流：

        START → phase1_analysis → (clarify?) → phase2_strategy
              → phase3_generate → phase4_summary → END
        """
        builder = StateGraph(WorkflowState)

        # 添加节点
        builder.add_node("phase1_analysis", self._phase1_analysis)
        builder.add_node("human_clarification", self._human_clarification)
        builder.add_node("phase2_strategy", self._phase2_strategy)
        builder.add_node("phase3_generate", self._phase3_generate)
        builder.add_node("phase4_summary", self._phase4_summary)

        # 构建边
        builder.add_edge(START, "phase1_analysis")

        # Phase1 后条件路由：需要澄清 or 直接进 Phase2
        builder.add_conditional_edges(
            "phase1_analysis",
            self._route_after_phase1,
            {"clarify": "human_clarification", "continue": "phase2_strategy", "end": END},
        )

        # 澄清后条件路由
        builder.add_conditional_edges(
            "human_clarification",
            self._route_after_clarification,
            {"continue": "phase2_strategy", "re_analyze": "phase1_analysis", "end": END},
        )

        # Phase2 → Phase3 → Phase4 → END 顺序执行
        builder.add_edge("phase2_strategy", "phase3_generate")
        builder.add_edge("phase3_generate", "phase4_summary")
        builder.add_edge("phase4_summary", END)

        return builder.compile(checkpointer=self.checkpointer)

    # ==================== 多模态内容构建 ====================

    @staticmethod
    def _build_document_content(state: WorkflowState) -> list:
        """构建文档多模态消息内容（RAG 上下文 + 文本 + 表格 + 图片）"""
        content = []

        # 注入 RAG 检索到的项目知识库上下文（放在需求文档之前，提供全局背景）
        rag_context = state.get("rag_context", "")
        if rag_context:
            content.append({
                "type": "text",
                "text": (
                    "## 项目知识库参考上下文\n\n"
                    "以下内容来自项目知识库中与当前需求相关的文档片段，"
                    "请结合这些上下文信息理解需求文档，避免因信息不完整而产生假设或猜测。\n\n"
                    f"{rag_context}\n\n---\n\n"
                ),
            })

        # 添加文档 markdown 内容
        doc_text = f"## 需求文档内容\n\n{state['document_content']}"

        # 添加表格信息
        if state.get("tables"):
            doc_text += "\n\n## 文档中的表格\n"
            for t in state["tables"]:
                doc_text += f"\n### {t['caption']}\n{t['markdown']}\n"

        content.append({"type": "text", "text": doc_text})

        # 添加图片作为多模态输入
        images = state.get("images", [])
        if images:
            content.append({"type": "text", "text": "\n\n## 文档中的图片\n"})
            for img in images:
                if img.get("base64"):
                    content.append({"type": "text", "text": f"\n### {img.get('caption', '图片')}\n"})
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img['base64']}"}
                    })

        return content

    # ==================== 4 阶段节点实现 ====================

    def _phase1_analysis(self, state: WorkflowState) -> dict:
        """
        Phase 1：文档结构识别 + 需求分析与澄清 + 模块对称性检查

        System prompt: role.md + phase1_analysis.md (~140 行)
        Human message: RAG 上下文 + 原始文档 + 表格 + 图片
        """
        if self.on_step:
            self.on_step("phase1_analysis")
        system_prompt = load_phase_prompt("phase1_analysis")

        instruction = (
            "请严格按照上述工作流程，完成步骤0（文档结构识别）、步骤1（需求分析与澄清）、"
            "步骤1.5（模块对称性检查）的全部内容并输出结果。\n\n"
            "如果在分析过程中发现需要澄清的高优先级问题，请在输出中明确标注全部需要澄清的问题（高、中、低优先级）"
            '"无法继续生成测试用例，存在以下问题需要澄清"，并列出待澄清问题。'
        )

        multimodal_content = self._build_document_content(state)
        multimodal_content.append({"type": "text", "text": f"\n\n{instruction}"})

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=multimodal_content),
        ]

        response = self.llm.invoke(messages)
        response_text = response.content

        # 判断是否有待澄清问题
        clarification_marker = "无法继续生成测试用例，存在以下问题需要澄清"
        has_clarification = clarification_marker in response_text
        clarification_questions = ""

        if has_clarification:
            marker_pos = response_text.find(clarification_marker)
            clarification_questions = response_text[marker_pos:].strip()

        return {
            "messages": [response],
            "analysis_result": response_text,
            "has_clarification": has_clarification,
            "clarification_questions": clarification_questions,
            "current_step": "phase1_complete",
        }

    def _phase2_strategy(self, state: WorkflowState) -> dict:
        """
        Phase 2：测试策略与设计思路 + 业务流程闭环验证 + 自我检查

        System prompt: role.md + phase2_strategy.md (~90 行)
        Human message: Phase1 精炼结论 + 原始文档（兜底参考）
        """
        if self.on_step:
            self.on_step("phase2_strategy")
        system_prompt = load_phase_prompt("phase2_strategy")

        # 构建上下文：Phase1 的结论 + 原始文档
        context_text = (
            "## 前序分析结论（Phase 1 输出）\n\n"
            f"{state['analysis_result']}\n\n"
            "---\n\n"
            f"## 原始需求文档（参考用）\n\n{state['document_content']}"
        )

        instruction = (
            "请基于上述前序分析结论和原始需求文档，严格完成步骤2（测试策略与设计思路）、"
            "步骤2.5（业务流程闭环验证）、步骤2.9（用例生成前自我检查）的全部内容并输出结果。"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{context_text}\n\n{instruction}"),
        ]

        response = self.llm.invoke(messages)

        return {
            "messages": [response],
            "strategy_result": response.content,
            "current_step": "phase2_complete",
        }

    def _phase3_generate(self, state: WorkflowState) -> dict:
        """
        Phase 3：生成测试用例

        System prompt: role.md + phase3_generate.md（可被用户自定义模板覆盖输出格式部分）
        Human message: Phase1 结论 + Phase2 结论 + 原始文档 + RAG 上下文
        """
        if self.on_step:
            self.on_step("phase3_generate")
        # 如果用户提供了自定义模板 prompt，使用它替换 phase3 的默认 prompt
        custom_prompt = state.get("system_prompt", "")
        if custom_prompt:
            role_text = (PROMPTS_DIR / "role.md").read_text(encoding="utf-8")
            system_prompt = f"{role_text}\n\n---\n\n{custom_prompt}"
        else:
            system_prompt = load_phase_prompt("phase3_generate")

        # 构建上下文：前序结论 + 原始文档 + RAG
        context_parts = [
            "## 前序分析结论（Phase 1 输出）\n\n",
            state["analysis_result"],
            "\n\n---\n\n",
            "## 测试策略（Phase 2 输出）\n\n",
            state["strategy_result"],
            "\n\n---\n\n",
            f"## 原始需求文档\n\n{state['document_content']}",
        ]

        rag_context = state.get("rag_context", "")
        if rag_context:
            context_parts.extend([
                "\n\n---\n\n",
                "## 项目知识库参考上下文\n\n",
                rag_context,
            ])

        context_text = "".join(context_parts)

        instruction = (
            "请基于上述前序分析结论、测试策略和原始需求文档，"
            "严格完成步骤3（生成测试用例）的全部内容。\n\n"
            "将所有测试用例整合到一个 Markdown 表格中统一输出，用例数量不限制，一次性全部生成完毕。"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{context_text}\n\n{instruction}"),
        ]

        response = self.llm.invoke(messages)

        return {
            "messages": [response],
            "cases_markdown": response.content,
            "current_step": "phase3_complete",
        }

    def _phase4_summary(self, state: WorkflowState) -> dict:
        """
        Phase 4：测试覆盖度总结

        System prompt: role.md + phase4_summary.md
        Human message: Phase1 结论 + Phase2 结论 + Phase3 用例
        """
        if self.on_step:
            self.on_step("phase4_summary")
        system_prompt = load_phase_prompt("phase4_summary")

        context_text = (
            "## 前序分析结论（Phase 1 输出）\n\n"
            f"{state['analysis_result']}\n\n"
            "---\n\n"
            "## 测试策略（Phase 2 输出）\n\n"
            f"{state['strategy_result']}\n\n"
            "---\n\n"
            "## 生成的测试用例（Phase 3 输出）\n\n"
            f"{state['cases_markdown']}"
        )

        instruction = (
            "请基于上述分析结论、测试策略和已生成的测试用例，"
            "完成步骤4（测试覆盖度总结）的全部内容。"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{context_text}\n\n{instruction}"),
        ]

        response = self.llm.invoke(messages)
        summary_text = response.content

        # 拼接完整报告：各阶段输出按顺序合并
        full_report = "\n\n---\n\n".join([
            state["analysis_result"],
            state["strategy_result"],
            state["cases_markdown"],
            summary_text,
        ])

        return {
            "messages": [response],
            "report_markdown": full_report,
            "summary_result": summary_text,
            "current_step": "phase4_complete",
        }

    # ==================== 人机澄清节点 ====================

    @staticmethod
    def _human_clarification(state: WorkflowState) -> dict:
        """人机澄清节点 - 等待用户输入"""
        user_input = interrupt({
            "type": "clarification_needed",
            "questions": state["clarification_questions"],
            "message": "请提供澄清信息，或输入'忽略待澄清内容，继续生成'跳过，或输入'停止生成'终止",
        })

        clarification_text = user_input.get("clarification_input", "")

        if clarification_text == "停止生成":
            return {"is_stopped": True}

        if clarification_text == "忽略待澄清内容，继续生成":
            return {
                "has_clarification": False,
                "messages": [HumanMessage(content="用户选择忽略澄清问题，继续生成测试用例")],
            }

        # Put clarification into analysis_result so phase2/3/4 can see it
        updated_analysis = (
            state["analysis_result"]
            + f"\n\n## 用户澄清补充信息\n\n{clarification_text}"
        )

        return {
            "has_clarification": False,
            "analysis_result": updated_analysis,
            "messages": [HumanMessage(content=f"用户澄清信息：\n{clarification_text}")],
        }

    # ==================== 路由函数 ====================

    @staticmethod
    def _route_after_phase1(state: WorkflowState) -> str:
        """Phase1 之后的路由：有澄清问题 → clarify，否则 → continue"""
        if state.get("is_stopped"):
            return "end"
        if state.get("has_clarification"):
            return "clarify"
        return "continue"

    @staticmethod
    def _route_after_clarification(state: WorkflowState) -> str:
        """澄清之后的路由：停止 → end，否则 → continue"""
        if state.get("is_stopped"):
            return "end"
        return "continue"

    # ==================== 对外接口 ====================

    def start(
        self,
        parsed_doc: ParsedDocument,
        template_prompt: Optional[str] = None,
        rag_context: str = "",
    ) -> tuple[str, dict]:
        """
        启动工作流

        Args:
            parsed_doc: 解析后的文档
            template_prompt: 用户自定义模板（仅覆盖 Phase3 的输出格式部分），可为空
            rag_context: RAG 检索到的项目知识库上下文，可为空
        """
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [],
            "document_content": parsed_doc.markdown,
            "images": parsed_doc.images,
            "tables": parsed_doc.tables,
            "system_prompt": template_prompt or "",
            "current_step": "start",
            "has_clarification": False,
            "clarification_questions": "",
            "report_markdown": "",
            "is_stopped": False,
            "rag_context": rag_context,
            # 阶段中间结果初始化
            "analysis_result": "",
            "strategy_result": "",
            "cases_markdown": "",
            "summary_result": "",
        }

        result = self.graph.invoke(initial_state, config=config)
        return thread_id, result

    def resume(self, thread_id: str, clarification_input: str) -> dict:
        """恢复工作流（用户提供澄清信息后）"""
        config = {"configurable": {"thread_id": thread_id}}
        resume_command = Command(resume={"clarification_input": clarification_input})
        return self.graph.invoke(resume_command, config=config)

    def get_state(self, thread_id: str) -> dict:
        """获取工作流当前状态"""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config)
