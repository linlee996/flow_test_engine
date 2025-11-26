package models

import (
	"time"
)

type TaskStatus int

const (
	// TaskStatusRunning 任务运行中
	TaskStatusRunning TaskStatus = 0
	// TaskStatusFinished 任务完成
	TaskStatusFinished TaskStatus = 1
	// TaskStatusFailed 运行失败
	TaskStatusFailed TaskStatus = 2
)

const TableNameWorkflowTask = "task"

var TaskColumns = &TaskColumn{
	ID:               "id",
	OriginalFilename: "original_filename",
	LocalFilePath:    "local_file_path",
	FilePath:         "file_path",
	Status:           "status",
	LangflowRunID:    "langflow_run_id",
	OutputFile:       "output_file",
	DownloadFile:     "download_file",
	UploadFileID:     "upload_file_id",
	OutputFileID:     "output_file_id",
	ErrorMessage:     "error_message",
	FinishedAt:       "finished_at",
	CreatedAt:        "created_at",
	UpdatedAt:        "updated_at",
}

type TaskColumn struct {
	ID               string
	OriginalFilename string
	LocalFilePath    string
	FilePath         string
	Status           string
	LangflowRunID    string
	OutputFile       string
	DownloadFile     string
	UploadFileID     string
	OutputFileID     string
	ErrorMessage     string
	FinishedAt       string
	CreatedAt        string
	UpdatedAt        string
}

type Task struct {
	ID               uint       `json:"id" gorm:"primaryKey;autoIncrement;comment:主键ID"`
	OriginalFilename string     `json:"original_filename" gorm:"size:255;not null;comment:原始文件名"`
	LocalFilePath    string     `json:"local_file_path" gorm:"size:500;comment:本地上传文件路径"`
	FilePath         string     `json:"file_path" gorm:"size:500;comment:Langflow文件路径"`
	Status           TaskStatus `json:"status" gorm:"not null;comment:任务状态[1.运行中;2.任务完成;3.任务失败]"`
	LangflowRunID    string     `json:"langflow_run_id" gorm:"size:255;comment:Langflow运行ID"`
	OutputFile       string     `json:"output_file" gorm:"size:500;comment:输出Excel文件名称"`
	DownloadFile     string     `json:"download_file" gorm:"size:500;comment:下载Excel文件名称"`
	UploadFileID     string     `json:"upload_file_id" gorm:"size:255;comment:Langflow上传文件ID"`
	OutputFileID     string     `json:"output_file_id" gorm:"size:255;comment:Langflow输出文件ID"`
	ErrorMessage     string     `json:"error_message" gorm:"type:text;comment:错误信息"`
	FinishedAt       *time.Time `json:"finished_at" gorm:"comment:完成时间"`
	CreatedAt        time.Time  `json:"created_at" gorm:"autoCreateTime;comment:创建时间"`
	UpdatedAt        time.Time  `json:"updated_at" gorm:"autoUpdateTime;comment:更新时间"`
}

func (*Task) TableName() string {
	return TableNameWorkflowTask
}
