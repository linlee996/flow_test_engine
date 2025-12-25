import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            window.location.href = '/';
        }
        return Promise.reject(error);
    }
);

export * from './types';
import type {
    Task,
    TaskListResponse,
    Template,
    UploadResponse
} from './types';

export const taskService = {
    getTasks: async (page = 1, pageSize = 10): Promise<TaskListResponse> => {
        const response = await api.get<TaskListResponse>('/tasks', {
            params: { page, page_size: pageSize },
        });
        return response.data;
    },

    createTask: async (data: {
        file_path: string;
        original_filename: string;
        download_filename?: string;
        template_id?: number | null;
        provider: string;
        model: string;
        advanced_parsing?: boolean;
    }): Promise<Task> => {
        const response = await api.post<Task>('/task/create', data);
        return response.data;
    },

    clarifyTask: async (taskId: number, clarificationInput: string): Promise<Task> => {
        const response = await api.post<Task>(`/task/${taskId}/clarify`, {
            clarification_input: clarificationInput,
        });
        return response.data;
    },

    getSummary: async (taskId: number): Promise<{ summary: string }> => {
        const response = await api.get<{ summary: string }>(`/task/${taskId}/summary`);
        return response.data;
    },

    deleteTask: async (taskId: number) => {
        const response = await api.delete(`/tasks/${taskId}`);
        return response.data;
    },

    uploadFile: async (file: File): Promise<UploadResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post<UploadResponse>('/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    getDownloadUrl: (taskId: number) => `/api/v1/download/${taskId}`,

    downloadFile: async (taskId: number) => {
        const response = await api.get(`/download/${taskId}`, {
            responseType: 'blob',
        });

        // Extract filename from Content-Disposition header
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'test_cases.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
            }
        }

        // Create blob URL and trigger download
        const blob = new Blob([response.data], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    },
};

export const templateService = {
    getTemplates: async (): Promise<Template[]> => {
        const response = await api.get<Template[]>('/templates');
        return response.data;
    },

    createTemplate: async (data: { name: string; fields: { name: string; description: string }[]; is_default?: boolean }): Promise<Template> => {
        const response = await api.post<Template>('/templates', data);
        return response.data;
    },

    updateTemplate: async (data: { id: number; name: string; fields: { name: string; description: string }[]; is_default?: boolean }): Promise<Template> => {
        const response = await api.put<Template>('/templates', data);
        return response.data;
    },

    deleteTemplate: async (id: number) => {
        const response = await api.delete(`/templates/${id}`);
        return response.data;
    },
};

// 旧版 LLM Config API 已删除,现在使用 /llm-configs/provider-* 相关的新版 API
export const llmConfigService = {};


export const authService = {
    login: async (data: { username: string; password: string }) => {
        const response = await api.post<{ token: string; username: string }>('/auth/login', data);
        return response.data;
    },
};
