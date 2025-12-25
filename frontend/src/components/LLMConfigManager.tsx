import React, { useState, useEffect, useCallback } from 'react';
import { Bot, Eye, EyeOff, RefreshCw, Zap, Plus, Trash2 } from 'lucide-react';
import { Button } from './ui/Button';

import styles from './LLMConfigManager.module.css';

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

interface ProviderListItem {
    provider: string;
    name: string;
    is_configured: boolean;
    is_available: boolean;
    model_count: number;
}

interface ProviderModel {
    id: number;
    model_name: string;
    is_custom: boolean;
}

import openaiLogo from '../assets/images/openai.png';
import geminiLogo from '../assets/images/gemini.png';
import anthropicLogo from '../assets/images/anthropic.png';
import deepseekLogo from '../assets/images/deepseek.png';
import kimiLogo from '../assets/images/kimi.png';
import openrouterLogo from '../assets/images/openrouter.png';

interface ProviderConfig {
    id: number;
    provider: string;
    base_url: string;
    is_available: boolean;
    models: ProviderModel[];
}


// 厂商图标/颜色映射 - 支持 6 个厂商
// The 'icon' property now holds a React node instead of a string
const PROVIDER_STYLES: Record<string, { icon: React.ReactNode; gradient: string }> = {
    openai: { icon: <img src={openaiLogo} alt="OpenAI" width={24} height={24} />, gradient: '#000000' },
    gemini: { icon: <img src={geminiLogo} alt="Gemini" width={24} height={24} />, gradient: '#ffffff' },
    anthropic: { icon: <img src={anthropicLogo} alt="Anthropic" width={24} height={24} />, gradient: '#ffffff' },
    deepseek: { icon: <img src={deepseekLogo} alt="DeepSeek" width={24} height={24} />, gradient: '#ffffff' },
    kimi: { icon: <img src={kimiLogo} alt="Kimi" width={24} height={24} />, gradient: '#000000' },
    openrouter: { icon: <img src={openrouterLogo} alt="OpenRouter" width={24} height={24} />, gradient: '#000000' },
    custom: { icon: <Bot size={24} />, gradient: 'linear-gradient(135deg, #6b7280, #374151)' },
};

// 厂商默认 Base URL（非 openai 厂商使用固定 URL）
const PROVIDER_DEFAULT_URLS: Record<string, string> = {
    openai: 'https://api.openai.com',
    gemini: 'https://generativelanguage.googleapis.com',
    anthropic: 'https://api.anthropic.com',
    deepseek: 'https://api.deepseek.com',
    kimi: 'https://api.moonshot.cn',
    openrouter: 'https://openrouter.ai/api',
};

export const LLMConfigManager: React.FC = () => {
    const [providers, setProviders] = useState<ProviderListItem[]>([]);
    const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
    const [config, setConfig] = useState<ProviderConfig | null>(null);

    // 表单状态
    const [baseUrl, setBaseUrl] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [showApiKey, setShowApiKey] = useState(false);
    const [newModelName, setNewModelName] = useState('');

    // 这里的 TestStatus 需要改为记录特定模型的测试状态
    const [modelTestStatus, setModelTestStatus] = useState<Record<string, { type: 'success' | 'error' | 'loading'; message: string }>>({});
    const [fetchStatus, setFetchStatus] = useState<{ type: 'success' | 'error' | 'loading'; message: string } | null>(null);
    const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error' | 'loading'; message: string } | null>(null);

    // 加载厂商列表
    const loadProviders = useCallback(async () => {
        try {
            const data = await api.fetch('/llm-configs/provider-list');
            setProviders(data);

            // 默认选择第一个已配置的或第一个
            if (!selectedProvider && data.length > 0) {
                const configured = data.find((p: ProviderListItem) => p.is_configured);
                setSelectedProvider(configured?.provider || data[0].provider);
            }
        } catch (err) {
            console.error('Failed to load providers', err);
        }
    }, [selectedProvider]);

    // 加载选中厂商的配置
    const loadConfig = useCallback(async (provider: string) => {
        setModelTestStatus({});
        setFetchStatus(null);
        setSaveStatus(null);

        try {
            const data = await api.fetch(`/llm-configs/provider-configs/${provider}`);
            setConfig(data);
            if (data) {
                setBaseUrl(data.base_url);
                setApiKey(''); // 不显示已保存的 API Key
            } else {
                // 未配置时使用默认 URL
                setBaseUrl(PROVIDER_DEFAULT_URLS[provider] || '');
                setApiKey('');
            }
        } catch (err) {
            setConfig(null);
            setBaseUrl(PROVIDER_DEFAULT_URLS[provider] || '');
            setApiKey('');
        }
    }, []);

    useEffect(() => {
        loadProviders();
    }, []);

    useEffect(() => {
        if (selectedProvider) {
            loadConfig(selectedProvider);
        }
    }, [selectedProvider, loadConfig]);

    // 保存配置
    const handleSave = async () => {
        if (!selectedProvider || !baseUrl.trim()) return;

        // 如果是新配置，必须提供 API Key
        if (!config && !apiKey.trim()) {
            setSaveStatus({ type: 'error', message: '请输入 API Key' });
            return;
        }

        setSaveStatus({ type: 'loading', message: '保存中...' });
        try {
            await api.fetch(`/llm-configs/provider-configs/${selectedProvider}`, {
                method: 'PUT',
                body: JSON.stringify({
                    base_url: baseUrl,
                    api_key: apiKey, // Send empty string if empty, backend will ignore
                }),
            });
            setSaveStatus({ type: 'success', message: '保存成功' });
            loadProviders();
            loadConfig(selectedProvider);
            setTimeout(() => setSaveStatus(null), 2000);
        } catch (err: any) {
            setSaveStatus({ type: 'error', message: err.message || '保存失败' });
        }
    };

    // 测试特定模型连接
    const handleTestModel = async (modelName: string) => {
        if (!selectedProvider || !baseUrl.trim() || (!config && !apiKey.trim())) {
            alert('请先填写 Base URL 和 API Key');
            return;
        }

        setModelTestStatus(prev => ({ ...prev, [modelName]: { type: 'loading', message: '测试中...' } }));

        try {
            // 使用新端点测试特定模型
            const result = await api.fetch(`/llm-configs/provider-configs/${selectedProvider}/models/${encodeURIComponent(modelName)}/test`, {
                method: 'POST',
                body: JSON.stringify({
                    base_url: baseUrl,
                    api_key: apiKey || '',
                    // model_name is in path
                }),
            });

            setModelTestStatus(prev => ({
                ...prev,
                [modelName]: {
                    type: result.success ? 'success' : 'error',
                    message: result.message
                }
            }));

            if (result.success) {
                loadProviders(); // 更新可用状态
                // 3秒后清除成功状态
                setTimeout(() => {
                    setModelTestStatus(prev => {
                        const next = { ...prev };
                        delete next[modelName];
                        return next;
                    });
                }, 3000);
            }
        } catch (err: any) {
            setModelTestStatus(prev => ({
                ...prev,
                [modelName]: { type: 'error', message: err.message || '测试失败' }
            }));
        }
    };

    // 获取模型
    const handleFetchModels = async () => {
        if (!selectedProvider || !baseUrl.trim() || (!config && !apiKey.trim())) {
            setFetchStatus({ type: 'error', message: '请先填写 Base URL 和 API Key' });
            return;
        }

        setFetchStatus({ type: 'loading', message: '获取中...' });
        try {
            const result = await api.fetch(`/llm-configs/provider-configs/${selectedProvider}/fetch-models`, {
                method: 'POST',
                body: JSON.stringify({
                    base_url: baseUrl,
                    api_key: apiKey || '',
                }),
            });
            setFetchStatus({
                type: result.success ? 'success' : 'error',
                message: result.success ? `获取到 ${result.models.length} 个模型` : result.message,
            });
            if (result.success) {
                loadConfig(selectedProvider);
                loadProviders();
            }
        } catch (err: any) {
            setFetchStatus({ type: 'error', message: err.message || '获取失败' });
        }
    };

    // 添加自定义模型
    const handleAddModel = async () => {
        if (!selectedProvider || !newModelName.trim()) return;

        try {
            await api.fetch(`/llm-configs/provider-configs/${selectedProvider}/models`, {
                method: 'POST',
                body: JSON.stringify({ model_name: newModelName }),
            });
            setNewModelName('');
            loadConfig(selectedProvider);
            loadProviders();
        } catch (err: any) {
            alert(err.message || '添加失败');
        }
    };

    // 删除模型
    const handleDeleteModel = async (modelName: string) => {
        if (!selectedProvider) return;

        try {
            await api.fetch(`/llm-configs/provider-configs/${selectedProvider}/models/${encodeURIComponent(modelName)}`, {
                method: 'DELETE',
            });
            loadConfig(selectedProvider);
            loadProviders();
        } catch (err: any) {
            alert(err.message || '删除失败');
        }
    };

    const getProviderStyle = (provider: string) => PROVIDER_STYLES[provider] || PROVIDER_STYLES['custom'];
    const currentProviderInfo = providers.find(p => p.provider === selectedProvider);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2>模型配置 (LLM Configuration)</h2>
            </div>

            <div className={styles.layout}>
                {/* 左侧厂商列表 */}
                <div className={styles.providerList}>
                    {providers.map((p) => {
                        const style = getProviderStyle(p.provider);
                        return (
                            <button
                                key={p.provider}
                                className={`${styles.providerItem} ${selectedProvider === p.provider ? styles.active : ''} ${p.is_configured ? styles.configured : ''}`}
                                onClick={() => setSelectedProvider(p.provider)}
                            >
                                <div className={styles.providerIcon} style={{ background: style.gradient }}>
                                    {style.icon}
                                </div>
                                <span className={styles.providerName}>{p.name}</span>
                                <div
                                    className={`${styles.statusDot} ${p.is_available ? styles.available : p.is_configured ? styles.configured : styles.unconfigured}`}
                                />
                            </button>
                        );
                    })}
                </div>

                {/* 右侧配置面板 */}
                <div className={styles.configPanel}>
                    {!selectedProvider ? (
                        <div className={styles.emptyPanel}>
                            <Bot size={48} />
                            <p>请从左侧选择一个提供商进行配置</p>
                        </div>
                    ) : (
                        <>
                            <div className={styles.configHeader}>
                                <div
                                    className={styles.providerIcon}
                                    style={{ background: getProviderStyle(selectedProvider).gradient, width: 36, height: 36 }}
                                >
                                    {getProviderStyle(selectedProvider).icon}
                                </div>
                                <div>
                                    <h3>{currentProviderInfo?.name || selectedProvider}</h3>
                                    <p className={styles.configSubtitle}>
                                        {config?.is_available ? '✓ 连接正常' : config ? '配置已保存' : '未配置'}
                                    </p>
                                </div>
                            </div>

                            <div className={styles.form}>
                                <div className={styles.field}>
                                    <label>Base URL {selectedProvider !== 'openai' && <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85em' }}>(固定)</span>}</label>
                                    <input
                                        className={styles.input}
                                        value={baseUrl}
                                        onChange={(e) => setBaseUrl(e.target.value)}
                                        placeholder="https://api.openai.com"
                                        readOnly={selectedProvider !== 'openai'}
                                        style={selectedProvider !== 'openai' ? { backgroundColor: 'var(--color-bg-secondary)', cursor: 'not-allowed' } : undefined}
                                    />
                                </div>

                                <div className={styles.field}>
                                    <label>API Key</label>
                                    <div className={styles.inputWrapper}>
                                        <input
                                            className={`${styles.input} ${styles.inputWithIcon}`}
                                            type={showApiKey ? 'text' : 'password'}
                                            value={apiKey}
                                            onChange={(e) => setApiKey(e.target.value)}
                                            placeholder={config ? '(保持不变请留空)' : 'sk-...'}
                                        />
                                        <div className={styles.inputIcon}>
                                            <button
                                                className={styles.iconButton}
                                                onClick={() => setShowApiKey(!showApiKey)}
                                                type="button"
                                            >
                                                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div className={styles.actions}>
                                    <Button
                                        size="sm"
                                        onClick={handleSave}
                                        isLoading={saveStatus?.type === 'loading'}
                                    >
                                        保存配置
                                    </Button>
                                    {/* Removed Global Test Button */}
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        icon={<RefreshCw size={14} />}
                                        onClick={handleFetchModels}
                                        isLoading={fetchStatus?.type === 'loading'}
                                    >
                                        获取模型列表
                                    </Button>
                                </div>

                                {(saveStatus) && (
                                    <div className={`${styles.statusMessage} ${styles[saveStatus.type]}`}>
                                        {saveStatus.message}
                                    </div>
                                )}
                                {fetchStatus && (
                                    <div className={`${styles.statusMessage} ${styles[fetchStatus.type]}`}>
                                        {fetchStatus.message}
                                    </div>
                                )}
                            </div>

                            {/* 模型列表 */}
                            <div className={styles.modelSection}>
                                <div className={styles.modelHeader}>
                                    <h4>模型列表 ({config?.models.length || 0})</h4>
                                </div>

                                <div className={styles.addModelRow}>
                                    <input
                                        className={styles.input}
                                        value={newModelName}
                                        onChange={(e) => setNewModelName(e.target.value)}
                                        placeholder="添加自定义模型名称..."
                                        onKeyDown={(e) => e.key === 'Enter' && handleAddModel()}
                                    />
                                    <Button size="sm" icon={<Plus size={14} />} onClick={handleAddModel}>
                                        添加
                                    </Button>
                                </div>

                                <div className={styles.modelList}>
                                    {config?.models.map((m) => {
                                        const status = modelTestStatus[m.model_name];
                                        return (
                                            <div key={m.id} className={styles.modelItem}>
                                                <span className={`${styles.modelName} ${m.is_custom ? styles.custom : ''}`}>
                                                    {m.model_name}
                                                    {m.is_custom && ' (自定义)'}
                                                </span>
                                                <div className={styles.modelItemActions}>
                                                    {/* Test Button for specific model */}
                                                    <button
                                                        className={`${styles.iconButton} ${status ? styles[status.type] : ''}`}
                                                        onClick={() => handleTestModel(m.model_name)}
                                                        title={status?.message || "测试模型连接"}
                                                    >
                                                        <Zap size={14} />
                                                    </button>
                                                    <button
                                                        className={styles.iconButton}
                                                        onClick={() => handleDeleteModel(m.model_name)}
                                                        title="删除模型"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {(!config?.models || config.models.length === 0) && (
                                        <div className={styles.emptyModels}>
                                            暂无模型。请使用"获取模型列表"或手动添加。
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};
