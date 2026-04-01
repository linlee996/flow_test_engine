import React, { useState, useEffect } from 'react';
import { Upload } from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Select } from './ui/Select';
import { GroupedSelect } from './ui/GroupedSelect';
import { taskService, templateService, knowledgeService, type Template, type Project } from '../services/api';
import styles from './CreateTaskModal.module.css';

// API 服务
const api = {
    baseURL: '/api/v1',
    async fetch(url: string, options: RequestInit = {}) {
        const token = localStorage.getItem('token');
        const response = await fetch(`${this.baseURL}${url}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
                ...options.headers,
            },
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `HTTP ${response.status}`);
        }
        return response.json();
    },
};

interface ModelGroup {
    provider: string;
    name: string;
    models: string[];
}

interface CreateTaskModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
    isOpen,
    onClose,
    onSuccess,
}) => {
    const [file, setFile] = useState<File | null>(null);
    const [filename, setFilename] = useState('');
    const [templateId, setTemplateId] = useState<string>('');
    const [selectedModel, setSelectedModel] = useState<string>(''); // 格式: "provider:model"
    const [templates, setTemplates] = useState<Template[]>([]);
    const [modelGroups, setModelGroups] = useState<ModelGroup[]>([]);
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (isOpen) {
            loadData();
            setFile(null);
            setFilename('');
            setTemplateId('');
            setSelectedModel('');
            setSelectedProjectId('');
            setError('');
        }
    }, [isOpen]);

    const LAST_SELECTED_MODEL_KEY = 'last_selected_model';

    const loadData = async () => {
        try {
            const [templatesData, groupsData, projectsData] = await Promise.all([
                templateService.getTemplates(),
                api.fetch('/llm-configs/model-groups'),
                knowledgeService.getProjects(),
            ]);
            setTemplates(templatesData);
            setModelGroups(groupsData);
            setProjects(projectsData.projects || []);

            // 尝试恢复上次选择的模型
            const lastSelected = localStorage.getItem(LAST_SELECTED_MODEL_KEY);
            let modelToSelect = '';

            if (lastSelected) {
                // 验证上次选择的模型是否仍然有效
                const [provider, model] = lastSelected.split(':');
                const group = groupsData.find((g: ModelGroup) => g.provider === provider);
                if (group && group.models.includes(model)) {
                    modelToSelect = lastSelected;
                }
            }

            // 如果没有有效的上次选择，则默认选择第一个
            if (!modelToSelect && groupsData.length > 0 && groupsData[0].models.length > 0) {
                modelToSelect = `${groupsData[0].provider}:${groupsData[0].models[0]}`;
            }

            if (modelToSelect) {
                setSelectedModel(modelToSelect);
            }
        } catch (err) {
            console.error('Failed to load data', err);
        }
    };

    // 保存选择的模型
    useEffect(() => {
        if (selectedModel) {
            localStorage.setItem(LAST_SELECTED_MODEL_KEY, selectedModel);
        }
    }, [selectedModel]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError('');
        }
    };

    const handleSubmit = async () => {
        if (!file) {
            setError('请选择文件');
            return;
        }
        if (!filename.trim()) {
            setError('请输入输出文件名');
            return;
        }
        if (!selectedModel) {
            setError('请选择模型');
            return;
        }

        const [provider, model] = selectedModel.split(':');
        if (!provider || !model) {
            setError('无效的模型选择');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            const uploadRes = await taskService.uploadFile(file);
            await taskService.createTask({
                file_path: uploadRes.file_path,
                original_filename: uploadRes.original_filename,
                download_filename: filename,
                template_id: templateId ? parseInt(templateId) : null,
                provider: provider,
                model: model,
                project_id: selectedProjectId ? parseInt(selectedProjectId) : null,
            });

            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || '创建任务失败');
        } finally {
            setIsLoading(false);
        }
    };

    // 转换为 GroupedSelect 需要的格式
    const groupedOptions = modelGroups.map(g => ({
        group: g.provider,
        label: g.name,
        options: g.models,
    }));

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="新建任务"
            footer={
                <>
                    <Button variant="ghost" onClick={onClose} disabled={isLoading}>
                        取消
                    </Button>
                    <Button onClick={handleSubmit} isLoading={isLoading}>
                        创建任务
                    </Button>
                </>
            }
        >
            <div className={styles.form}>
                <div className={styles.field}>
                    <label>模型选择 *</label>
                    <GroupedSelect
                        value={selectedModel}
                        onChange={setSelectedModel}
                        groups={groupedOptions}
                        placeholder="请选择模型"
                    />
                    {modelGroups.length === 0 && (
                        <small style={{ color: 'var(--color-warning)' }}>
                            暂无可用模型，请先在设置中配置提供商。
                        </small>
                    )}
                </div>

                <div className={styles.field}>
                    <label>上传文档 *</label>
                    <div className={styles.fileInput}>
                        <input
                            type="file"
                            id="file-upload"
                            accept=".pdf,.doc,.docx,.txt,.md"
                            onChange={handleFileChange}
                            className={styles.hiddenInput}
                        />
                        <label htmlFor="file-upload" className={styles.uploadBox}>
                            <Upload size={24} />
                            <span>{file ? file.name : '点击上传 PDF, DOC, DOCX, TXT, MD'}</span>
                        </label>
                    </div>
                </div>

                <div className={styles.field}>
                    <label>输出文件名 *</label>
                    <input
                        type="text"
                        className={styles.input}
                        placeholder="例如：需求测试用例"
                        value={filename}
                        onChange={(e) => setFilename(e.target.value)}
                    />
                    <small>系统会自动附加时间戳</small>
                </div>

                <div className={styles.field}>
                    <label>选择模板</label>
                    <Select
                        value={templateId}
                        onChange={setTemplateId}
                        options={[
                            { value: '', label: '默认模板' },
                            ...templates.map((t) => ({
                                value: t.id.toString(),
                                label: `${t.name} ${t.is_default ? '(默认)' : ''}`,
                            })),
                        ]}
                        placeholder="请选择模板"
                    />
                </div>

                <div className={styles.field}>
                    <label>关联知识库</label>
                    <Select
                        value={selectedProjectId}
                        onChange={setSelectedProjectId}
                        options={[
                            { value: '', label: '不关联' },
                            ...projects.filter(p => p.doc_count > 0).map((p) => ({
                                value: p.id.toString(),
                                label: `${p.name} (${p.doc_count} 个文档)`,
                            })),
                        ]}
                        placeholder="选择知识库项目"
                    />
                    <small style={{ color: 'var(--color-text-muted)' }}>
                        关联知识库后，生成时会自动检索项目文档补充上下文，减少幻觉。
                    </small>
                </div>

                {error && <div className={styles.error}>{error}</div>}
            </div>
        </Modal>
    );
};
