import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v1',
    timeout: 10000,
});

export interface ApiResponse<T = any> {
    code: number;
    message: string;
    data: T;
}

export interface Task {
    task_id: string;
    original_filename: string;
    created_at: string;
    finished_at?: string;
    status: number; // 0: Running, 1: Finished, 2: Failed
    error_message?: string;
}

export interface TaskListResponse {
    list: Task[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
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
    upload_file: string;
}

export const taskService = {
    getTasks: async (page = 1, pageSize = 10) => {
        const response = await api.get<ApiResponse<TaskListResponse>>('/tasks', {
            params: { page, page_size: pageSize },
        });
        return response.data;
    },

    createTask: async (data: {
        file_path: string;
        upload_file: string;
        download_file: string;
        template_id?: number | null;
    }) => {
        const response = await api.post<ApiResponse>('/task/create', data);
        return response.data;
    },

    deleteTask: async (taskId: string) => {
        const response = await api.delete<ApiResponse>(`/tasks/${taskId}`);
        return response.data;
    },

    uploadFile: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post<ApiResponse<UploadResponse>>('/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },
};

export const templateService = {
    getTemplates: async () => {
        const response = await api.get<ApiResponse<Template[]>>('/templates');
        return response.data;
    },

    saveTemplate: async (data: { id?: number; name: string; fields: TemplateField[] }) => {
        if (data.id) {
            const response = await api.put<ApiResponse>(`/templates`, data);
            return response.data;
        } else {
            const response = await api.post<ApiResponse>('/templates', data);
            return response.data;
        }
    },

    deleteTemplate: async (id: number) => {
        const response = await api.delete<ApiResponse>(`/templates/${id}`);
        return response.data;
    },
};
