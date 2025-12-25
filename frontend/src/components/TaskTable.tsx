import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Trash2, FileText, MessageSquare, FileCheck } from 'lucide-react';
import { type Task, TaskStatus, taskService } from '../services/api';
import { Button } from './ui/Button';
import { StatusBadge } from './ui/StatusBadge';
import { Card } from './ui/Card';
import { Tooltip } from './ui/Tooltip';
import { ClarificationModal } from './ClarificationModal';
import { SummaryModal } from './SummaryModal';
import styles from './TaskTable.module.css';

interface TaskTableProps {
    tasks: Task[];
    isLoading: boolean;
    onDelete: (id: number, filename: string) => void;
    onRefresh: () => void;
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks, isLoading, onDelete, onRefresh }) => {
    const [clarifyTask, setClarifyTask] = useState<Task | null>(null);
    const [summaryTask, setSummaryTask] = useState<Task | null>(null);
    const [downloadingTaskId, setDownloadingTaskId] = useState<number | null>(null);

    const handleClarifySubmit = async (taskId: number, input: string) => {
        await taskService.clarifyTask(taskId, input);
        setClarifyTask(null);
        onRefresh();
    };

    const handleDownload = async (task: Task) => {
        try {
            setDownloadingTaskId(task.task_id);
            await taskService.downloadFile(task.task_id);
        } catch (err) {
            console.error('Download failed', err);
        } finally {
            setDownloadingTaskId(null);
        }
    };

    if (isLoading) {
        return (
            <Card>
                <div className={styles.loading}>
                    <div className={styles.spinner} />
                    <p>正在加载任务...</p>
                </div>
            </Card>
        );
    }

    if (tasks.length === 0) {
        return (
            <Card>
                <div className={styles.empty}>
                    <div className={styles.emptyIcon}>📝</div>
                    <h3>暂无任务</h3>
                    <p>创建一个新任务开始使用</p>
                </div>
            </Card>
        );
    }

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    return (
        <>
            <Card className={styles.tableCard}>
                <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>任务 ID</th>
                                <th>文件名</th>
                                <th>创建时间</th>
                                <th>完成时间</th>
                                <th>状态</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence mode="popLayout">
                                {tasks.map((task, index) => (
                                    <React.Fragment key={task.task_id}>
                                        <motion.tr
                                            className={styles.row}
                                            initial={{ opacity: 0, y: 20, scale: 0.98 }}
                                            animate={{ opacity: 1, y: 0, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{
                                                type: "spring",
                                                stiffness: 500,
                                                damping: 30,
                                                mass: 1,
                                                delay: index * 0.05
                                            }}
                                        >
                                            <td className={styles.mono}>#{task.task_id}</td>
                                            <td>
                                                <Tooltip content={task.original_filename}>
                                                    <div className={styles.filename}>
                                                        <FileText size={16} style={{ flexShrink: 0 }} />
                                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                            {task.original_filename}
                                                        </span>
                                                    </div>
                                                </Tooltip>
                                            </td>
                                            <td className={styles.dateColumn}>{formatDate(task.created_at)}</td>
                                            <td className={styles.dateColumn}>
                                                {task.finished_at ? formatDate(task.finished_at) : '-'}
                                            </td>
                                            <td>
                                                <StatusBadge status={task.status} />
                                            </td>
                                            <td>
                                                <div className={styles.actions}>
                                                    {/* 澄清按钮 */}
                                                    {task.status === TaskStatus.CLARIFYING && (
                                                        <Button
                                                            size="sm"
                                                            variant="secondary"
                                                            icon={<MessageSquare size={14} />}
                                                            onClick={() => setClarifyTask(task)}
                                                        >
                                                            Clarify
                                                        </Button>
                                                    )}
                                                    {/* 完成状态：下载和查看总结 */}
                                                    {task.status === TaskStatus.FINISHED && (
                                                        <>
                                                            <Button
                                                                size="sm"
                                                                variant="primary"
                                                                icon={<Download size={14} />}
                                                                onClick={() => handleDownload(task)}
                                                                isLoading={downloadingTaskId === task.task_id}
                                                            >
                                                                Download
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                variant="secondary"
                                                                icon={<FileCheck size={14} />}
                                                                onClick={() => setSummaryTask(task)}
                                                            >
                                                                查看总结
                                                            </Button>
                                                        </>
                                                    )}
                                                    <Button
                                                        size="sm"
                                                        variant="danger"
                                                        icon={<Trash2 size={14} />}
                                                        onClick={() => onDelete(task.task_id, task.original_filename)}
                                                    >
                                                        删除
                                                    </Button>
                                                </div>
                                            </td>
                                        </motion.tr>
                                        {/* 错误信息行 */}
                                        {task.error_message && (
                                            <motion.tr
                                                className={styles.errorRow}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                            >
                                                <td colSpan={6}>
                                                    <div className={styles.error}>
                                                        ❌ 错误: {task.error_message}
                                                    </div>
                                                </td>
                                            </motion.tr>
                                        )}
                                        {/* 澄清问题预览行 */}
                                        {task.status === TaskStatus.CLARIFYING && task.clarification_message && (
                                            <motion.tr
                                                className={styles.clarifyRow}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                            >
                                                <td colSpan={6}>
                                                    <div className={styles.clarifyPreview}>
                                                        💬 需要澄清 - 点击 "Clarify" 按钮进行回复
                                                    </div>
                                                </td>
                                            </motion.tr>
                                        )}
                                    </React.Fragment>
                                ))}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* 澄清模态框 */}
            {clarifyTask && (
                <ClarificationModal
                    isOpen={!!clarifyTask}
                    task={clarifyTask}
                    onClose={() => setClarifyTask(null)}
                    onSubmit={handleClarifySubmit}
                />
            )}

            {/* 总结模态框 */}
            {summaryTask && (
                <SummaryModal
                    isOpen={!!summaryTask}
                    task={summaryTask}
                    onClose={() => setSummaryTask(null)}
                />
            )}
        </>
    );
};
