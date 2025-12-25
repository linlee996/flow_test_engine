import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, SkipForward, StopCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Task } from '../services/api';
import { Button } from './ui/Button';
import styles from './ClarificationModal.module.css';

interface ClarificationModalProps {
    isOpen: boolean;
    task: Task;
    onClose: () => void;
    onSubmit: (taskId: number, input: string) => Promise<void>;
}

export const ClarificationModal: React.FC<ClarificationModalProps> = ({
    isOpen,
    task,
    onClose,
    onSubmit,
}) => {
    const [input, setInput] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (value: string) => {
        setIsSubmitting(true);
        try {
            await onSubmit(task.task_id, value);
        } finally {
            setIsSubmitting(false);
            setInput('');
        }
    };

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
                        <h2>💬 需要澄清</h2>
                        <button className={styles.closeBtn} onClick={onClose}>
                            <X size={20} />
                        </button>
                    </div>

                    <div className={styles.content}>
                        <div className={styles.taskInfo}>
                            <span className={styles.label}>任务:</span>
                            <span>{task.original_filename}</span>
                        </div>

                        <div className={styles.questions}>
                            <h3>AI 提出的问题:</h3>
                            <div className={styles.questionContent}>
                                {task.clarification_message ? (
                                    <ReactMarkdown>{task.clarification_message}</ReactMarkdown>
                                ) : (
                                    '没有具体的问题。'
                                )}
                            </div>
                        </div>

                        <div className={styles.inputSection}>
                            <label>您的回复:</label>
                            <textarea
                                className={styles.textarea}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="请输入您的补充说明..."
                                rows={4}
                            />
                        </div>
                    </div>

                    <div className={styles.footer}>
                        <div className={styles.quickActions}>
                            <Button
                                variant="secondary"
                                size="sm"
                                icon={<SkipForward size={14} />}
                                onClick={() => handleSubmit('忽略待澄清内容，继续生成')}
                                disabled={isSubmitting}
                            >
                                跳过并继续
                            </Button>
                            <Button
                                variant="danger"
                                size="sm"
                                icon={<StopCircle size={14} />}
                                onClick={() => handleSubmit('停止生成')}
                                disabled={isSubmitting}
                            >
                                停止生成
                            </Button>
                        </div>
                        <Button
                            variant="primary"
                            icon={<Send size={14} />}
                            onClick={() => handleSubmit(input)}
                            disabled={!input.trim() || isSubmitting}
                            isLoading={isSubmitting}
                        >
                            提交澄清
                        </Button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};
