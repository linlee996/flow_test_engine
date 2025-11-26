package utils

import (
	"time"
)

// TimeFormat 时间格式化常量
const TimeFormat = "2006-01-02 15:04:05"

// FormatTime 格式化 time.Time 为字符串
func FormatTime(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.Format(TimeFormat)
}

// FormatTimePtr 格式化 *time.Time 为字符串
func FormatTimePtr(t *time.Time) string {
	if t == nil || t.IsZero() {
		return ""
	}
	return t.Format(TimeFormat)
}
