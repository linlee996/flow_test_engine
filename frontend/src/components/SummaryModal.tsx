import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Task } from '../services/api';
import styles from './SummaryModal.module.css';

interface SummaryModalProps {
    isOpen: boolean;
    task: Task;
    onClose: () => void;
}

export const SummaryModal: React.FC<SummaryModalProps> = ({
    isOpen,
    task,
    onClose,
}) => {
    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                className={styles.overlay}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
            >
                <motion.div
                    className={styles.modal}
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className={styles.header}>
                        <div className={styles.headerTitle}>
                            <FileText size={20} />
                            <h2>测试用例总结</h2>
                        </div>
                        <button className={styles.closeBtn} onClick={onClose}>
                            <X size={20} />
                        </button>
                    </div>

                    <div className={styles.content}>
                        <div className={styles.taskInfo}>
                            <span className={styles.label}>任务:</span>
                            <span>{task.original_filename}</span>
                        </div>

                        <div className={styles.summary}>
                            {task.summary_content ? (
                                <div className={styles.summaryContent}>
                                    <ReactMarkdown>{task.summary_content}</ReactMarkdown>
                                </div>
                            ) : (
                                <div className={styles.noSummary}>
                                    此任务暂无总结。
                                </div>
                            )}
                        </div>
                    </div>

                    <div className={styles.footer}>
                        <button className={styles.closeButton} onClick={onClose}>
                            关闭
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};
