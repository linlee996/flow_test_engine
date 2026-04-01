import React, { useState, useEffect } from 'react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { knowledgeService, type EmbeddingProviderInfo } from '../services/api';
import styles from './CreateProjectModal.module.css';

interface CreateProjectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
    isOpen,
    onClose,
    onSuccess,
}) => {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [embeddingProvider, setEmbeddingProvider] = useState('');
    const [embeddingModel, setEmbeddingModel] = useState('');
    const [providers, setProviders] = useState<EmbeddingProviderInfo[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (isOpen) {
            setName('');
            setDescription('');
            setEmbeddingProvider('');
            setEmbeddingModel('');
            setError('');
            loadProviders();
        }
    }, [isOpen]);

    const loadProviders = async () => {
        try {
            const data = await knowledgeService.getEmbeddingProviders();
            setProviders(data);
            // 默认选中第一个已配置的厂商
            const configured = data.find(p => p.is_configured);
            if (configured) {
                setEmbeddingProvider(configured.provider);
                setEmbeddingModel(configured.default_model);
            }
        } catch (err) {
            console.error('Failed to load embedding providers', err);
        }
    };

    const handleProviderChange = (provider: string) => {
        setEmbeddingProvider(provider);
        const info = providers.find(p => p.provider === provider);
        if (info) {
            setEmbeddingModel(info.default_model);
        }
    };

    const handleSubmit = async () => {
        if (!name.trim()) {
            setError('请输入项目名称');
            return;
        }
        if (!embeddingProvider) {
            setError('请选择 Embedding 厂商');
            return;
        }
        if (!embeddingModel.trim()) {
            setError('请输入 Embedding 模型名');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            await knowledgeService.createProject({
                name: name.trim(),
                description: description.trim() || undefined,
                embedding_provider: embeddingProvider,
                embedding_model: embeddingModel.trim(),
            });
            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || '创建失败');
        } finally {
            setIsLoading(false);
        }
    };

    const configuredProviders = providers.filter(p => p.is_configured);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="创建知识库项目"
            footer={
                <>
                    <Button variant="ghost" onClick={onClose} disabled={isLoading}>
                        取消
                    </Button>
                    <Button onClick={handleSubmit} isLoading={isLoading}>
                        创建
                    </Button>
                </>
            }
        >
            <div className={styles.form}>
                <div className={styles.field}>
                    <label>项目名称 *</label>
                    <input
                        type="text"
                        className={styles.input}
                        placeholder="例如：CRM系统V2.0"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                </div>

                <div className={styles.field}>
                    <label>项目描述</label>
                    <textarea
                        className={styles.textarea}
                        placeholder="描述项目的业务背景和范围..."
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                    />
                </div>

                <div className={styles.field}>
                    <label>Embedding 厂商 *</label>
                    {configuredProviders.length > 0 ? (
                        <select
                            className={styles.select}
                            value={embeddingProvider}
                            onChange={(e) => handleProviderChange(e.target.value)}
                        >
                            <option value="">请选择</option>
                            {configuredProviders.map(p => (
                                <option key={p.provider} value={p.provider}>
                                    {p.name}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <p className={styles.warningText}>
                            暂无支持 Embedding 的已配置厂商，请先在模型配置中添加 OpenAI 或 Gemini。
                        </p>
                    )}
                    <small className={styles.hint}>
                        用于将文档转换为向量，需选择支持 Embedding API 的厂商
                    </small>
                </div>

                <div className={styles.field}>
                    <label>Embedding 模型 *</label>
                    <input
                        type="text"
                        className={styles.input}
                        placeholder="例如：text-embedding-3-small"
                        value={embeddingModel}
                        onChange={(e) => setEmbeddingModel(e.target.value)}
                    />
                    <small className={styles.hint}>
                        通常使用厂商默认模型即可，也可手动输入其他模型名
                    </small>
                </div>

                {error && <div className={styles.error}>{error}</div>}
            </div>
        </Modal>
    );
};
