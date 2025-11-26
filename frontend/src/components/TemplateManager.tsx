import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Eye } from 'lucide-react';
import { templateService, type Template, type TemplateField } from '../services/api';
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
        fields: [{ name: '', description: '' }],
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
            setTemplates(data.data);
        } catch (err) {
            console.error('Failed to load templates', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingTemplate({ name: '', fields: [{ name: '', description: '' }] });
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
            await templateService.saveTemplate(editingTemplate as any);
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

    const updateField = (index: number, key: keyof TemplateField, value: string) => {
        const newFields = [...(editingTemplate.fields || [])];
        newFields[index] = { ...newFields[index], [key]: value };
        setEditingTemplate({ ...editingTemplate, fields: newFields });
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2>Templates</h2>
                <Button onClick={handleCreate} icon={<Plus size={16} />}>
                    Create Template
                </Button>
            </div>

            <div className={styles.grid}>
                {isLoading && <p>Loading templates...</p>}
                {!isLoading && templates.map((template) => (
                    <Card key={template.id} className={styles.card}>
                        <div className={styles.cardHeader}>
                            <h3>{template.name}</h3>
                            {template.is_default && <span className={styles.badge}>Default</span>}
                        </div>
                        <div className={styles.cardBody}>
                            <p>{template.fields.length} fields configured</p>
                            <div className={styles.actions}>
                                {!template.is_system && (
                                    <>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            icon={<Edit2 size={14} />}
                                            onClick={() => handleEdit(template)}
                                        >
                                            Edit
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="danger"
                                            icon={<Trash2 size={14} />}
                                            onClick={() => handleDeleteClick(template.id)}
                                        >
                                            Delete
                                        </Button>
                                    </>
                                )}
                                {template.is_system && (
                                    <>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            icon={<Eye size={14} />}
                                            onClick={() => handleView(template)}
                                        >
                                            View
                                        </Button>
                                        <span className={styles.systemBadge}>System Template</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={isViewMode ? 'View Template' : (editingTemplate.id ? 'Edit Template' : 'Create Template')}
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
                            {isViewMode ? 'Close' : 'Cancel'}
                        </Button>
                        {!isViewMode && <Button onClick={handleSave}>Save Template</Button>}
                    </>
                }
            >
                <div className={styles.form}>
                    <div className={styles.field}>
                        <label>Template Name</label>
                        <input
                            className={styles.input}
                            value={editingTemplate.name}
                            onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                            placeholder="e.g. Simple Template"
                            disabled={isViewMode}
                        />
                    </div>

                    <div className={styles.field}>
                        <label>Fields</label>
                        {editingTemplate.fields?.map((field, index) => (
                            <div key={index} className={styles.fieldRow}>
                                <input
                                    className={styles.input}
                                    placeholder="Field Name"
                                    value={field.name}
                                    onChange={(e) => updateField(index, 'name', e.target.value)}
                                    disabled={isViewMode}
                                />
                                <input
                                    className={styles.input}
                                    placeholder="Description"
                                    value={field.description}
                                    onChange={(e) => updateField(index, 'description', e.target.value)}
                                    disabled={isViewMode}
                                />
                                {!isViewMode && (
                                    <Button
                                        size="sm"
                                        variant="danger"
                                        onClick={() => removeField(index)}
                                        icon={<Trash2 size={14} />}
                                    />
                                )}
                            </div>
                        ))}
                        {!isViewMode && (
                            <Button size="sm" variant="secondary" onClick={addField} icon={<Plus size={14} />}>
                                Add Field
                            </Button>
                        )}
                    </div>
                </div>
            </Modal>

            <ConfirmModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={handleConfirmDelete}
                title="Delete Template"
                message="Delete this template?"
                confirmText="Delete"
                cancelText="Cancel"
            />
        </div >
    );
};
