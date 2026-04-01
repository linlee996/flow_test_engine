export const TaskStatus = {
    RUNNING: 0,
    CLARIFYING: 1,
    FINISHED: 2,
    FAILED: 3,
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export interface Task {
    task_id: number;
    original_filename: string;
    created_at: string;
    finished_at?: string;
    status: TaskStatus;
    error_message?: string;
    clarification_message?: string;
    summary_content?: string;
    current_step?: string;
}

export interface TaskListResponse {
    total: number;
    tasks: Task[];
}

export interface TemplateField {
    name: string;
    description: string;
}

export interface Template {
    id: number;
    name: string;
    fields: TemplateField[];
    is_default: boolean;
    is_system: boolean;
    created_at: string;
    updated_at: string;
}

export interface UploadResponse {
    file_path: string;
    original_filename: string;
}

// LLM 配置相关
export interface LLMConfig {
    id: number;
    name: string;
    provider: string;
    base_url: string;
    model: string;
    is_default: boolean;
    created_at: string;
    updated_at: string;
}

export interface ProviderInfo {
    provider: string;
    base_url: string;
    models: string[];
}

// 知识库相关
export interface Project {
    id: number;
    name: string;
    description?: string;
    embedding_provider: string;
    embedding_model: string;
    doc_count: number;
    created_at: string;
    updated_at: string;
}

export interface ProjectListResponse {
    total: number;
    projects: Project[];
}

export interface KnowledgeDocument {
    id: number;
    project_id: number;
    original_filename: string;
    file_size: number;
    chunk_count: number;
    status: 'processing' | 'ready' | 'failed';
    error_message?: string;
    created_at: string;
}

export interface EmbeddingProviderInfo {
    provider: string;
    name: string;
    default_model: string;
    is_configured: boolean;
}

export interface KnowledgeSearchResult {
    content: string;
    metadata: Record<string, unknown>;
    distance: number;
}
