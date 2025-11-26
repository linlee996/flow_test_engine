package models

import "time"

const TableNameCaseTemplate = "case_template"

type CaseTemplate struct {
	ID          uint      `json:"id" gorm:"primaryKey;autoIncrement;comment:主键ID"`
	Name        string    `json:"name" gorm:"size:255;not null;uniqueIndex;comment:模板名称"`
	Content     string    `json:"content" gorm:"type:text;not null;comment:模板内容"`
	IsDefault   bool      `json:"is_default" gorm:"default:false;comment:是否为默认模板"`
	IsSystem    bool      `json:"is_system" gorm:"default:false;comment:是否为系统模板(不可删除)"`
	CreatedAt   time.Time `json:"created_at" gorm:"autoCreateTime;comment:创建时间"`
	UpdatedAt   time.Time `json:"updated_at" gorm:"autoUpdateTime;comment:更新时间"`
}

func (*CaseTemplate) TableName() string {
	return TableNameCaseTemplate
}
