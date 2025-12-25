"""LangGraph 用例生成工作流 - 含人机澄清循环"""
import uuid
from pathlib import Path
from typing import TypedDict, Annotated, Optional
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

# 加载 backend/config/prompt.md 作为系统 prompt
PROMPT_FILE = Path(__file__).parent.parent.parent / "config" / "prompt.md"


def load_system_prompt() -> str:
    """加载 backend/config/prompt.md 作为系统 prompt"""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")


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
    system_prompt: str  # 系统 prompt（来自 config/prompt.md，可被模板替换）
    current_step: str  # 当前执行步骤
    has_clarification: bool  # 是否有待澄清问题
    clarification_questions: str  # 待澄清问题
    report_markdown: str  # 最终输出的 markdown 报告
    is_stopped: bool  # 用户是否停止生成


class CaseGeneratorWorkflow:
    """用例生成工作流"""

    def __init__(self, api_key: str, base_url: str, model: str, provider: str = "openai"):
        self.llm = create_llm(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()
        self.base_prompt = load_system_prompt()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        builder = StateGraph(WorkflowState)

        builder.add_node("analyze_document", self._analyze_document)
        builder.add_node("human_clarification", self._human_clarification)
        builder.add_node("generate_cases", self._generate_cases)

        builder.add_edge(START, "analyze_document")

        builder.add_conditional_edges(
            "analyze_document",
            self._route_after_analysis,
            {"clarify": "human_clarification", "generate": "generate_cases", "end": END}
        )

        builder.add_conditional_edges(
            "human_clarification",
            self._route_after_clarification,
            {"generate": "generate_cases", "analyze": "analyze_document", "end": END}
        )

        builder.add_edge("generate_cases", END)

        return builder.compile(checkpointer=self.checkpointer)

    @staticmethod
    def _build_multimodal_content(state: WorkflowState) -> list:
        """构建多模态消息内容（文本 + 图片）"""
        content = []

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

    def _analyze_document(self, state: WorkflowState) -> dict:
        """分析文档并生成完整的测试用例输出"""
        system_prompt = state["system_prompt"]

        # 构建完整执行指令
        analysis_instruction = """请严格按照系统提示中的工作流程，完整执行所有步骤，生成完整的测试用例报告。

如果在分析过程中发现需要澄清的问题，请在报告中明确标注"无法继续生成测试用例，存在以下问题需要澄清"，并列出待澄清问题。"""

        # 构建多模态消息
        multimodal_content = self._build_multimodal_content(state)
        multimodal_content.append({"type": "text", "text": f"\n\n{analysis_instruction}"})

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=multimodal_content),
        ]

        response = self.llm.invoke(messages)
        response_text = response.content

        # 判断是否有待澄清问题
        clarification_marker = "无法继续生成测试用例，存在以下问题需要澄清"
        clarification_questions = ""
        has_clarification = False

        if clarification_marker in response_text:
            marker_pos = response_text.find(clarification_marker)
            clarification_questions = response_text[marker_pos:].strip()
            has_clarification = True

        return {
            "messages": [response],
            "report_markdown": response_text,
            "has_clarification": has_clarification,
            "clarification_questions": clarification_questions,
            "current_step": "analysis_complete",
        }

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

        return {
            "messages": [HumanMessage(content=f"用户澄清信息：\n{clarification_text}")],
        }

    def _generate_cases(self, state: WorkflowState) -> dict:
        """澄清后重新生成完整的测试用例输出"""
        system_prompt = state["system_prompt"]

        # 构建完整执行指令 - 基于澄清信息重新生成
        generate_instruction = """基于用户提供的澄清信息继续完成后续步骤，生成完整的测试用例报告。"""

        # 构建多模态消息（包含文档内容）
        multimodal_content = self._build_multimodal_content(state)
        multimodal_content.append({"type": "text", "text": f"\n\n{generate_instruction}"})

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(state["messages"])
        messages.append(HumanMessage(content=multimodal_content))

        response = self.llm.invoke(messages)

        return {
            "messages": [response],
            "report_markdown": response.content,
            "has_clarification": False,
            "current_step": "generation_complete",
        }

    def _route_after_analysis(self, state: WorkflowState) -> str:
        if state.get("is_stopped"):
            return "end"
        if state.get("has_clarification"):
            return "clarify"
        # 没有待澄清问题，直接结束（report_markdown 已在 _analyze_document 中生成）
        return "end"

    def _route_after_clarification(self, state: WorkflowState) -> str:
        if state.get("is_stopped"):
            return "end"
        last_msg = state["messages"][-1] if state["messages"] else None
        if last_msg and ("待澄清问题" in str(last_msg.content) or "🔴" in str(last_msg.content)):
            return "analyze"
        return "generate"

    def start(self, parsed_doc: ParsedDocument, template_prompt: Optional[str] = None) -> tuple[str, dict]:
        """
        启动工作流
        template_prompt: 用户自定义模板，会替换 prompt.md 中的内容
        """
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        # 使用用户模板替换系统 prompt，或使用默认 prompt
        system_prompt = template_prompt if template_prompt else self.base_prompt

        initial_state = {
            "messages": [],
            "document_content": parsed_doc.markdown,
            "images": parsed_doc.images,
            "tables": parsed_doc.tables,
            "system_prompt": system_prompt,
            "current_step": "start",
            "has_clarification": False,
            "clarification_questions": "",
            "report_markdown": "",
            "is_stopped": False,
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
