import React from 'react';
import classNames from 'classnames';
import { Loader2, CheckCircle2, XCircle, HelpCircle, MessageCircleQuestion } from 'lucide-react';
import styles from './StatusBadge.module.css';

interface StatusBadgeProps {
    status: number; // 0: Running, 1: Clarifying, 2: Finished, 3: Failed
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
    const config = {
        0: { label: '运行中', icon: Loader2, className: styles.running, animate: true },
        1: { label: '需澄清', icon: MessageCircleQuestion, className: styles.clarifying, animate: true },
        2: { label: '已完成', icon: CheckCircle2, className: styles.finished, animate: false },
        3: { label: '失败', icon: XCircle, className: styles.failed, animate: false },
    };

    const { label, icon: Icon, className, animate } = config[status as keyof typeof config] || {
        label: '未知',
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
