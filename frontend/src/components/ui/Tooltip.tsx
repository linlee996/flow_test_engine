import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './Tooltip.module.css';

interface TooltipProps {
    content: string;
    children: React.ReactNode;
    delay?: number;
}

export const Tooltip: React.FC<TooltipProps> = ({ content, children, delay = 0.2 }) => {
    const [isVisible, setIsVisible] = useState(false);
    let timeout: ReturnType<typeof setTimeout>;

    const show = () => {
        timeout = setTimeout(() => setIsVisible(true), delay * 1000);
    };

    const hide = () => {
        clearTimeout(timeout);
        setIsVisible(false);
    };

    return (
        <div className={styles.container} onMouseEnter={show} onMouseLeave={hide}>
            {children}
            <AnimatePresence>
                {isVisible && (
                    <motion.div
                        className={styles.tooltip}
                        initial={{ opacity: 0, y: 5, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                    >
                        {content}
                        <div className={styles.arrow} />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
