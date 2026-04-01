import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, FileText, Upload, Trash2, Database, Search, RefreshCw, FolderOpen } from 'lucide-react';
import { Button } from './ui/Button';
import { ConfirmModal } from './ui/ConfirmModal';
import { CreateProjectModal } from './CreateProjectModal';
import { knowledgeService, type Project, type KnowledgeDocument } from '../services/api';
import styles from './KnowledgeManager.module.css';

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const KnowledgeManager: React.FC = () => {
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProject, setSelectedProject] = useState<Project | null>(null);
    const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<{ type: 'project' | 'document'; id: number; name: string } | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadProjects = useCallback(async () => {
        try {
            const data = await knowledgeService.getProjects();
            setProjects(data.projects);
        } catch (err) {
            console.error('Failed to load projects', err);
        }
    }, []);

    const loadDocuments = useCallback(async (projectId: number) => {
        try {
            const docs = await knowledgeService.getDocuments(projectId);
            setDocuments(docs);
        } catch (err) {
            console.error('Failed to load documents', err);
        }
    }, []);

    useEffect(() => {
        loadProjects();
    }, [loadProjects]);

    useEffect(() => {
        if (selectedProject) {
            loadDocuments(selectedProject.id);
            // 轮询刷新处理中的文档状态
            const interval = setInterval(() => {
                loadDocuments(selectedProject.id);
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [selectedProject, loadDocuments]);

    const handleSelectProject = (project: Project) => {
        setSelectedProject(project);
    };

    const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || !e.target.files[0] || !selectedProject) return;

        const file = e.target.files[0];
        setIsUploading(true);

        try {
            await knowledgeService.uploadDocument(selectedProject.id, file);
            await loadDocuments(selectedProject.id);
            await loadProjects(); // 刷新文档计数
        } catch (err: any) {
            alert(err.response?.data?.detail || err.message || '上传失败');
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleConfirmDelete = async () => {
        if (!deleteTarget) return;
        try {
            if (deleteTarget.type === 'project') {
                await knowledgeService.deleteProject(deleteTarget.id);
                if (selectedProject?.id === deleteTarget.id) {
                    setSelectedProject(null);
                    setDocuments([]);
                }
                await loadProjects();
            } else {
                await knowledgeService.deleteDocument(deleteTarget.id);
                if (selectedProject) {
                    await loadDocuments(selectedProject.id);
                    await loadProjects();
                }
            }
        } catch (err: any) {
            alert(err.response?.data?.detail || err.message || '删除失败');
        } finally {
            setDeleteTarget(null);
        }
    };

    const renderDocStatus = (doc: KnowledgeDocument) => {
        if (doc.status === 'ready') {
            return <span className={styles.statusReady}>✓ {doc.chunk_count} 块</span>;
        }
        if (doc.status === 'processing') {
            return <span className={styles.statusProcessing}>⏳ 处理中</span>;
        }
        return (
            <span className={styles.statusFailed} title={doc.error_message || ''}>
                ✗ 失败
            </span>
        );
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2>知识库管理</h2>
                <Button
                    variant="primary"
                    icon={<Plus size={18} />}
                    onClick={() => setIsCreateModalOpen(true)}
                >
                    创建项目
                </Button>
            </div>

            {projects.length === 0 ? (
                <div className={styles.emptyState}>
                    <Database size={48} strokeWidth={1} />
                    <p>还没有知识库项目</p>
                    <p>创建一个项目，上传项目文档，在生成测试用例时自动检索相关上下文</p>
                    <Button variant="primary" icon={<Plus size={16} />} onClick={() => setIsCreateModalOpen(true)}>
                        创建第一个项目
                    </Button>
                </div>
            ) : (
                <div className={styles.layout}>
                    {/* 左侧：项目列表 */}
                    <div className={styles.sidebar}>
                        {projects.map(project => (
                            <div
                                key={project.id}
                                className={`${styles.projectCard} ${selectedProject?.id === project.id ? styles.active : ''}`}
                                onClick={() => handleSelectProject(project)}
                            >
                                <div className={styles.projectName}>{project.name}</div>
                                <div className={styles.projectMeta}>
                                    <span>{project.embedding_provider}</span>
                                    <span className={styles.docCount}>{project.doc_count} 个文档</span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* 右侧：项目详情 + 文档列表 */}
                    <div className={styles.detail}>
                        {selectedProject ? (
                            <>
                                <div className={styles.detailHeader}>
                                    <div>
                                        <div className={styles.detailTitle}>{selectedProject.name}</div>
                                        {selectedProject.description && (
                                            <div className={styles.detailDesc}>{selectedProject.description}</div>
                                        )}
                                    </div>
                                    <div className={styles.detailActions}>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            icon={<Trash2 size={14} />}
                                            onClick={() => setDeleteTarget({
                                                type: 'project',
                                                id: selectedProject.id,
                                                name: selectedProject.name,
                                            })}
                                        >
                                            删除项目
                                        </Button>
                                    </div>
                                </div>

                                <div className={styles.detailInfo}>
                                    <div className={styles.infoItem}>
                                        <span className={styles.infoLabel}>Embedding:</span>
                                        <span className={styles.infoValue}>
                                            {selectedProject.embedding_provider} / {selectedProject.embedding_model}
                                        </span>
                                    </div>
                                    <div className={styles.infoItem}>
                                        <span className={styles.infoLabel}>文档:</span>
                                        <span className={styles.infoValue}>{selectedProject.doc_count} 个</span>
                                    </div>
                                </div>

                                <div className={styles.docSection}>
                                    <div className={styles.docHeader}>
                                        <h3>文档列表</h3>
                                        <div className={styles.uploadArea}>
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                className={styles.hiddenInput}
                                                accept=".pdf,.doc,.docx,.txt,.md"
                                                onChange={handleUploadFile}
                                            />
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                icon={<Upload size={14} />}
                                                isLoading={isUploading}
                                                onClick={() => fileInputRef.current?.click()}
                                            >
                                                上传文档
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                icon={<RefreshCw size={14} />}
                                                onClick={() => loadDocuments(selectedProject.id)}
                                            >
                                                刷新
                                            </Button>
                                        </div>
                                    </div>

                                    {documents.length === 0 ? (
                                        <div className={styles.emptyState}>
                                            <FolderOpen size={36} strokeWidth={1} />
                                            <p>暂无文档，上传项目相关文档以构建知识库</p>
                                        </div>
                                    ) : (
                                        <div className={styles.docList}>
                                            {documents.map(doc => (
                                                <div key={doc.id} className={styles.docItem}>
                                                    <div className={styles.docInfo}>
                                                        <FileText size={18} className={styles.docIcon} />
                                                        <span className={styles.docName}>{doc.original_filename}</span>
                                                    </div>
                                                    <div className={styles.docMeta}>
                                                        <span className={styles.docSize}>{formatFileSize(doc.file_size)}</span>
                                                        {renderDocStatus(doc)}
                                                        <button
                                                            className={styles.deleteBtn}
                                                            onClick={() => setDeleteTarget({
                                                                type: 'document',
                                                                id: doc.id,
                                                                name: doc.original_filename,
                                                            })}
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className={styles.emptyState}>
                                <Search size={48} strokeWidth={1} />
                                <p>选择左侧的项目查看详情</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <CreateProjectModal
                isOpen={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                onSuccess={loadProjects}
            />

            <ConfirmModal
                isOpen={!!deleteTarget}
                onClose={() => setDeleteTarget(null)}
                onConfirm={handleConfirmDelete}
                title={deleteTarget?.type === 'project' ? '删除项目' : '删除文档'}
                message={
                    deleteTarget?.type === 'project'
                        ? `确定要删除项目 "${deleteTarget?.name}" 吗？所有关联文档和向量数据都将被永久删除。`
                        : `确定要删除文档 "${deleteTarget?.name}" 吗？`
                }
                confirmText="删除"
                cancelText="取消"
            />
        </div>
    );
};
