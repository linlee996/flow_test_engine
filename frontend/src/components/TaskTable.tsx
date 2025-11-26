import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Trash2, FileText } from 'lucide-react';
import type { Task } from '../services/api';
import { Button } from './ui/Button';
import { StatusBadge } from './ui/StatusBadge';
import { Card } from './ui/Card';
import { Tooltip } from './ui/Tooltip';
import styles from './TaskTable.module.css';

interface TaskTableProps {
    tasks: Task[];
    isLoading: boolean;
    onDelete: (id: string, filename: string) => void;
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks, isLoading, onDelete }) => {
    if (isLoading) {
        return (
            <Card>
                <div className={styles.loading}>
                    <div className={styles.spinner} />
                    <p>Loading tasks...</p>
                </div>
            </Card>
        );
    }

    if (tasks.length === 0) {
        return (
            <Card>
                <div className={styles.empty}>
                    <div className={styles.emptyIcon}>📝</div>
                    <h3>No tasks found</h3>
                    <p>Create a new task to get started</p>
                </div>
            </Card>
        );
    }

    return (
        <Card className={styles.tableCard}>
            <div className={styles.tableWrapper}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Filename</th>
                            <th>Created At</th>
                            <th>Finished At</th>
                            <th>Status</th>
                            <th>Actions</th>
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
                                        <td className={styles.mono}>{task.task_id.substring(0, 8)}...</td>
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
                                        <td className={styles.dateColumn}>{task.created_at}</td>
                                        <td className={styles.dateColumn}>{task.finished_at || '-'}</td>
                                        <td>
                                            <StatusBadge status={task.status} />
                                        </td>
                                        <td>
                                            <div className={styles.actions}>
                                                {task.status === 1 && (
                                                    <a
                                                        href={`/api/v1/download/${task.task_id}`}
                                                        className={styles.downloadLink}
                                                        download
                                                    >
                                                        <Button size="sm" variant="primary" icon={<Download size={14} />}>
                                                            Download
                                                        </Button>
                                                    </a>
                                                )}
                                                <Button
                                                    size="sm"
                                                    variant="danger"
                                                    icon={<Trash2 size={14} />}
                                                    onClick={() => onDelete(task.task_id, task.original_filename)}
                                                >
                                                    Delete
                                                </Button>
                                            </div>
                                        </td>
                                    </motion.tr>
                                    {task.error_message && (
                                        <motion.tr
                                            className={styles.errorRow}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                        >
                                            <td colSpan={6}>
                                                <div className={styles.error}>
                                                    ❌ Error: {task.error_message}
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
    );
};
