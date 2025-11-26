import React from 'react';
import classNames from 'classnames';
import { Loader2, CheckCircle2, XCircle, HelpCircle } from 'lucide-react';
import styles from './StatusBadge.module.css';

interface StatusBadgeProps {
    status: number; // 0: Running, 1: Finished, 2: Failed
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
    const config = {
        0: { label: 'Running', icon: Loader2, className: styles.running, animate: true },
        1: { label: 'Finished', icon: CheckCircle2, className: styles.finished, animate: false },
        2: { label: 'Failed', icon: XCircle, className: styles.failed, animate: false },
    };

    const { label, icon: Icon, className, animate } = config[status as keyof typeof config] || {
        label: 'Unknown',
        icon: HelpCircle,
        className: styles.unknown,
        animate: false,
    };

    return (
        <span className={classNames(styles.badge, className)}>
            <Icon size={14} className={classNames(styles.icon, { [styles.spin]: animate })} />
            {label}
        </span>
    );
};
