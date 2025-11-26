import React from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, FileText, Plus } from 'lucide-react';
import { Button } from './ui/Button';
import styles from './Layout.module.css';

interface LayoutProps {
    children: React.ReactNode;
    activeTab: 'tasks' | 'templates';
    onTabChange: (tab: 'tasks' | 'templates') => void;
    onCreateTask: () => void;
}

export const Layout: React.FC<LayoutProps> = ({
    children,
    activeTab,
    onTabChange,
    onCreateTask,
}) => {
    return (
        <div className={styles.layout}>
            <header className={styles.header}>
                <div className={styles.logo}>
                    <div className={styles.logoIcon}>
                        <svg width="28" height="28" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <defs>
                                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="#60A5FA" />
                                    <stop offset="100%" stopColor="#A78BFA" />
                                </linearGradient>
                                <filter id="logoGlow">
                                    <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                                    <feMerge>
                                        <feMergeNode in="coloredBlur" />
                                        <feMergeNode in="SourceGraphic" />
                                    </feMerge>
                                </filter>
                            </defs>
                            <path d="M55 5 L25 50 L50 50 L40 95 L85 40 L60 40 Z"
                                fill="url(#logoGrad)"
                                stroke="white"
                                strokeWidth="4"
                                strokeLinejoin="round"
                                filter="url(#logoGlow)"
                            />
                        </svg>
                    </div>
                    <h1>Flow Test Engine</h1>
                </div>
                <div className={styles.actions}>
                    <Button
                        variant="primary"
                        icon={<Plus size={18} />}
                        onClick={onCreateTask}
                    >
                        New Task
                    </Button>
                </div>
            </header>

            <div className={styles.container}>
                <aside className={styles.sidebar}>
                    <nav className={styles.nav}>
                        <button
                            className={`${styles.navItem} ${activeTab === 'tasks' ? styles.active : ''}`}
                            onClick={() => onTabChange('tasks')}
                        >
                            <LayoutDashboard size={20} />
                            Tasks
                        </button>
                        <button
                            className={`${styles.navItem} ${activeTab === 'templates' ? styles.active : ''}`}
                            onClick={() => onTabChange('templates')}
                        >
                            <FileText size={20} />
                            Templates
                        </button>
                    </nav>
                </aside>

                <main className={styles.main}>
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        {children}
                    </motion.div>
                </main>
            </div>
        </div>
    );
};
