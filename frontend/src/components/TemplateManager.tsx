import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Eye, Star, X } from 'lucide-react';
import { templateService, type Template } from '../services/api';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Modal } from './ui/Modal';
import { ConfirmModal } from './ui/ConfirmModal';
import styles from './TemplateManager.module.css';

export const TemplateManager: React.FC = () => {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingTemplate, setEditingTemplate] = useState<Partial<Template>>({
        name: '',
        fields: [],
        is_default: false,
    });
    const [isViewMode, setIsViewMode] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);

    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        setIsLoading(true);
        try {
            const data = await templateService.getTemplates();
            setTemplates(data);
        } catch (err) {
            console.error('Failed to load templates', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingTemplate({
            name: '',
            fields: [{ name: '', description: '' }],
            is_default: false
        });
        setIsViewMode(false);
        setIsModalOpen(true);
    };

    const handleEdit = (template: Template) => {
        setEditingTemplate(template);
        setIsViewMode(false);
        setIsModalOpen(true);
    };

    const handleView = (template: Template) => {
        setEditingTemplate(template);
        setIsViewMode(true);
        setIsModalOpen(true);
    };

    const handleDeleteClick = (id: number) => {
        setDeleteId(id);
    };

    const handleConfirmDelete = async () => {
        if (!deleteId) return;
        try {
            await templateService.deleteTemplate(deleteId);
            loadTemplates();
        } catch (err) {
            console.error('Failed to delete template', err);
        } finally {
            setDeleteId(null);
        }
    };

    const handleSave = async () => {
        try {
            if (editingTemplate.id) {
                await templateService.updateTemplate({
                    id: editingTemplate.id,
                    name: editingTemplate.name || '',
                    fields: editingTemplate.fields || [],
                    is_default: editingTemplate.is_default,
                });
            } else {
                await templateService.createTemplate({
                    name: editingTemplate.name || '',
                    fields: editingTemplate.fields || [],
                    is_default: editingTemplate.is_default,
                });
            }
            setIsModalOpen(false);
            loadTemplates();
        } catch (err) {
            console.error('Failed to save template', err);
        }
    };

    const addField = () => {
        setEditingTemplate({
            ...editingTemplate,
            fields: [...(editingTemplate.fields || []), { name: '', description: '' }],
        });
    };

    const removeField = (index: number) => {
        const newFields = [...(editingTemplate.fields || [])];
        newFields.splice(index, 1);
        setEditingTemplate({ ...editingTemplate, fields: newFields });
    };

    const updateField = (index: number, field: 'name' | 'description', value: string) => {
        const newFields = [...(editingTemplate.fields || [])];
        newFields[index][field] = value;
        setEditingTemplate({ ...editingTemplate, fields: newFields });
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2>模板管理</h2>
                <Button onClick={handleCreate} icon={<Plus size={16} />}>
                    创建模板
                </Button>
            </div>

            <div className={styles.grid}>
                {isLoading && <p>正在加载...</p>}
                {!isLoading && templates.length === 0 && (
                    <Card className={styles.emptyCard}>
                        <p>暂无模板，请创建！</p>
                    </Card>
                )}
                {!isLoading && templates.map((template) => (
                    <Card key={template.id} className={styles.card}>
                        <div className={styles.cardHeader}>
                            <h3>{template.name}</h3>
                            <div className={styles.badges}>
                                {template.is_default && (
                                    <span className={styles.badge}>
                                        <Star size={12} /> 默认
                                    </span>
                                )}
                                {template.is_system && (
                                    <span className={styles.systemBadge}>系统内置</span>
                                )}
                            </div>
                        </div>
                        <div className={styles.cardBody}>
                            <p className={styles.preview}>
                                {template.fields.length} 个字段：
                                {template.fields.slice(0, 3).map(f => f.name).join('、')}
                                {template.fields.length > 3 ? '...' : ''}
                            </p>
                            <div className={styles.actions}>
                                {!template.is_system ? (
                                    <>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            icon={<Edit2 size={14} />}
                                            onClick={() => handleEdit(template)}
                                        >
                                            编辑
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="danger"
                                            icon={<Trash2 size={14} />}
                                            onClick={() => handleDeleteClick(template.id)}
                                        >
                                            删除
                                        </Button>
                                    </>
                                ) : (
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        icon={<Eye size={14} />}
                                        onClick={() => handleView(template)}
                                    >
                                        查看
                                    </Button>
                                )}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={isViewMode ? '查看模板' : (editingTemplate.id ? '编辑模板' : '创建模板')}
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
                            {isViewMode ? '关闭' : '取消'}
                        </Button>
                        {!isViewMode && <Button onClick={handleSave}>保存模板</Button>}
                    </>
                }
            >
                <div className={styles.form}>
                    <div className={styles.field}>
                        <label>模板名称</label>
                        <input
                            className={styles.input}
                            value={editingTemplate.name}
                            onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                            placeholder="例如：API 测试模板"
                            disabled={isViewMode}
                        />
                    </div>

                    <div className={styles.field}>
                        <label>字段列表</label>
                        <div className={styles.fieldsList}>
                            {(editingTemplate.fields || []).map((field, index) => (
                                <div key={index} className={styles.fieldRow}>
                                    <input
                                        className={styles.fieldInput}
                                        value={field.name}
                                        onChange={(e) => updateField(index, 'name', e.target.value)}
                                        placeholder="字段名称"
                                        disabled={isViewMode}
                                    />
                                    <input
                                        className={styles.fieldInput}
                                        value={field.description}
                                        onChange={(e) => updateField(index, 'description', e.target.value)}
                                        placeholder="字段描述"
                                        disabled={isViewMode}
                                    />
                                    {!isViewMode && (
                                        <button
                                            className={styles.removeBtn}
                                            onClick={() => removeField(index)}
                                            type="button"
                                        >
                                            <X size={16} />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                        {!isViewMode && (
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={addField}
                                icon={<Plus size={14} />}
                            >
                                添加字段
                            </Button>
                        )}
                    </div>

                    {!isViewMode && (
                        <div className={styles.checkbox}>
                            <input
                                type="checkbox"
                                id="is_default"
                                checked={editingTemplate.is_default || false}
                                onChange={(e) => setEditingTemplate({ ...editingTemplate, is_default: e.target.checked })}
                            />
                            <label htmlFor="is_default">设为默认模板</label>
                        </div>
                    )}
                </div>
            </Modal>

            <ConfirmModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={handleConfirmDelete}
                title="删除模板"
                message="确定要删除这个模板吗？"
                confirmText="删除"
                cancelText="取消"
            />
        </div>
    );
};
