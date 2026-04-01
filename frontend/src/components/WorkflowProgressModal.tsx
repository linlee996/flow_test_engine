import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Activity, CheckCircle2, Loader2, Circle } from 'lucide-react';
import type { Task } from '../services/api';
import styles from './WorkflowProgressModal.module.css';

interface WorkflowProgressModalProps {
    isOpen: boolean;
    task: Task;
    onClose: () => void;
}

/** Workflow step definition */
interface StepDef {
    key: string;
    label: string;
}

/** All possible workflow steps in execution order */
const WORKFLOW_STEPS: StepDef[] = [
    { key: 'doc_parsing', label: '文档解析' },
    { key: 'rag_retrieval', label: 'RAG 知识库检索' },
    { key: 'phase1_analysis', label: '需求分析' },
    { key: 'phase2_strategy', label: '测试策略设计' },
    { key: 'phase3_generate', label: '用例生成' },
    { key: 'phase4_summary', label: '覆盖度总结' },
    { key: 'extracting', label: '结果提取' },
];

type StepStatus = 'completed' | 'running' | 'pending';

function getStepStatus(stepKey: string, currentStep: string | undefined): StepStatus {
    if (!currentStep) return 'pending';

    const currentIdx = WORKFLOW_STEPS.findIndex((s) => s.key === currentStep);
    const stepIdx = WORKFLOW_STEPS.findIndex((s) => s.key === stepKey);

    if (stepIdx < currentIdx) return 'completed';
    if (stepIdx === currentIdx) return 'running';
    return 'pending';
}

export const WorkflowProgressModal: React.FC<WorkflowProgressModalProps> = ({
    isOpen,
    task,
    onClose,
}) => {
    if (!isOpen) return null;

    const currentStep = task.current_step;

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
                            <Activity size={20} />
                            <h2>工作流进度</h2>
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

                        <div className={styles.stepList}>
                            {WORKFLOW_STEPS.map((step, index) => {
                                const status = getStepStatus(step.key, currentStep);
                                return (
                                    <div
                                        key={step.key}
                                        className={`${styles.stepItem} ${styles[status]}`}
                                    >
                                        <div className={styles.stepIndicator}>
                                            {/* Vertical connector line */}
                                            {index > 0 && (
                                                <div
                                                    className={`${styles.connector} ${
                                                        status !== 'pending'
                                                            ? styles.connectorActive
                                                            : ''
                                                    }`}
                                                />
                                            )}
                                            {/* Step icon */}
                                            <div className={styles.stepIcon}>
                                                {status === 'completed' && (
                                                    <CheckCircle2 size={20} />
                                                )}
                                                {status === 'running' && (
                                                    <Loader2
                                                        size={20}
                                                        className={styles.spin}
                                                    />
                                                )}
                                                {status === 'pending' && (
                                                    <Circle size={20} />
                                                )}
                                            </div>
                                        </div>
                                        <div className={styles.stepContent}>
                                            <span className={styles.stepLabel}>
                                                {step.label}
                                            </span>
                                            {status === 'running' && (
                                                <span className={styles.runningHint}>
                                                    运行中...
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
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
