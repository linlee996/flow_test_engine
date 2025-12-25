import React, { useState, useRef, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check } from 'lucide-react';
import styles from './Select.module.css';

interface OptionGroup {
    group: string;
    label: string;
    options: string[];
}

interface GroupedSelectProps {
    value: string; // 格式: "provider:model"
    onChange: (value: string) => void;
    groups: OptionGroup[];
    placeholder?: string;
    className?: string;
}

export const GroupedSelect: React.FC<GroupedSelectProps> = ({
    value,
    onChange,
    groups,
    placeholder = 'Select a model',
    className,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });

    // 解析当前值
    const [selectedProvider, selectedModel] = value ? value.split(':') : ['', ''];
    const selectedGroupLabel = groups.find(g => g.group === selectedProvider)?.label;
    const displayText = selectedModel ? `${selectedGroupLabel}/${selectedModel}` : '';

    useLayoutEffect(() => {
        const updatePosition = () => {
            if (containerRef.current && isOpen) {
                const rect = containerRef.current.getBoundingClientRect();
                setPosition({
                    top: rect.bottom + 4,
                    left: rect.left,
                    width: Math.max(rect.width, 300), // 至少 300px 宽
                });
            }
        };

        if (isOpen) {
            updatePosition();
            window.addEventListener('scroll', updatePosition, true);
            window.addEventListener('resize', updatePosition);
        }

        return () => {
            window.removeEventListener('scroll', updatePosition, true);
            window.removeEventListener('resize', updatePosition);
        };
    }, [isOpen]);

    const handleSelect = (provider: string, model: string) => {
        onChange(`${provider}:${model}`);
        setIsOpen(false);
    };

    // 检查是否没有任何可选模型
    const hasModels = groups.some(g => g.options.length > 0);

    return (
        <div className={`${styles.container} ${className || ''}`} ref={containerRef}>
            <div
                className={`${styles.trigger} ${isOpen ? styles.open : ''}`}
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className={displayText ? styles.value : styles.placeholder}>
                    {displayText || placeholder}
                </span>
                <ChevronDown size={16} className={`${styles.arrow} ${isOpen ? styles.arrowOpen : ''}`} />
            </div>

            {isOpen && createPortal(
                <div
                    className={styles.dropdown}
                    style={{
                        position: 'fixed',
                        top: position.top,
                        left: position.left,
                        width: position.width,
                        zIndex: 99999,
                        maxHeight: '400px',
                        overflowY: 'auto',
                    }}
                    data-select-dropdown
                >
                    {!hasModels ? (
                        <div className={styles.emptyMessage}>
                            No models available. Please configure a provider first.
                        </div>
                    ) : (
                        groups.map((group) => (
                            group.options.length > 0 && (
                                <div key={group.group} className={styles.group}>
                                    <div className={styles.groupHeader}>{group.label}</div>
                                    {group.options.map((model) => (
                                        <div
                                            key={`${group.group}:${model}`}
                                            className={`${styles.option} ${selectedProvider === group.group && selectedModel === model ? styles.selected : ''}`}
                                            onClick={() => handleSelect(group.group, model)}
                                        >
                                            <span>{model}</span>
                                            {selectedProvider === group.group && selectedModel === model && (
                                                <Check size={14} className={styles.check} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )
                        ))
                    )}
                </div>,
                document.body
            )}
        </div>
    );
};
