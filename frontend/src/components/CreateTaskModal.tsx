import React, { useState, useEffect } from 'react';
import { Upload } from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Select } from './ui/Select';
import { taskService, templateService, type Template } from '../services/api';
import styles from './CreateTaskModal.module.css';

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
    const [templates, setTemplates] = useState<Template[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (isOpen) {
            loadTemplates();
            setFile(null);
            setFilename('');
            setTemplateId('');
            setError('');
        }
    }, [isOpen]);

    const loadTemplates = async () => {
        try {
            const data = await templateService.getTemplates();
            setTemplates(data.data);
        } catch (err) {
            console.error('Failed to load templates', err);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError('');
        }
    };

    const handleSubmit = async () => {
        if (!file) {
            setError('Please select a file');
            return;
        }
        if (!filename.trim()) {
            setError('Please enter an output filename');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            // 1. Upload file
            const uploadRes = await taskService.uploadFile(file);

            // 2. Create task
            await taskService.createTask({
                file_path: uploadRes.data.file_path,
                upload_file: uploadRes.data.upload_file,
                download_file: filename,
                template_id: templateId ? parseInt(templateId) : null,
            });

            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.message || 'Failed to create task');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Create New Task"
            footer={
                <>
                    <Button variant="ghost" onClick={onClose} disabled={isLoading}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} isLoading={isLoading}>
                        Create Task
                    </Button>
                </>
            }
        >
            <div className={styles.form}>
                <div className={styles.field}>
                    <label>Upload Document *</label>
                    <div className={styles.fileInput}>
                        <input
                            type="file"
                            id="file-upload"
                            accept=".pdf,.doc,.docx,.txt"
                            onChange={handleFileChange}
                            className={styles.hiddenInput}
                        />
                        <label htmlFor="file-upload" className={styles.uploadBox}>
                            <Upload size={24} />
                            <span>{file ? file.name : 'Click to upload PDF, DOC, DOCX, TXT'}</span>
                        </label>
                    </div>
                </div>

                <div className={styles.field}>
                    <label>Output Filename *</label>
                    <input
                        type="text"
                        className={styles.input}
                        placeholder="e.g. Requirement_Test_Cases"
                        value={filename}
                        onChange={(e) => setFilename(e.target.value)}
                    />
                    <small>System will append timestamp automatically</small>
                </div>

                <div className={styles.field}>
                    <label>Template</label>
                    <Select
                        value={templateId}
                        onChange={setTemplateId}
                        options={[
                            { value: '', label: 'Default Template' },
                            ...templates.map((t) => ({
                                value: t.id.toString(),
                                label: `${t.name} ${t.is_default ? '(Default)' : ''}`,
                            })),
                        ]}
                        placeholder="Select a template"
                    />
                </div>

                {error && <div className={styles.error}>{error}</div>}
            </div>
        </Modal>
    );
};
