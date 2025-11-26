package dto

import (
	"flow_test_engine/internal/repo/models"
)

// TaskCreateRequest 创建工作流任务请求
type TaskCreateRequest struct {
	UploadFile   string `json:"upload_file" binding:"required"`   // 上传文件名称
	FilePath     string `json:"file_path" binding:"required"`     // 上传文件路径
	DownloadFile string `json:"download_file" binding:"required"` // 输出文件名称
	TemplateID   *uint  `json:"template_id"`                      // 用例模板ID，为空则使用默认模板
}

// TaskCreateResponse 创建工作流任务响应
type TaskCreateResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    struct {
		TaskID string `json:"task_id"`
		Status string `json:"status"`
	}
}

// TaskListRequest 任务列表请求参数
type TaskListRequest struct {
	Page             int    `json:"page"`
	PageSize         int    `json:"page_size"`
	TaskID           uint   `json:"task_id"`
	Status           string `json:"status"`
	OriginalFilename string `json:"original_filename"`
}

// TaskListResponse 任务列表响应参数
type TaskListResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    struct {
		List       []*TaskListItem `json:"list"`
		Total      int64           `json:"total"`
		Page       int             `json:"page"`
		PageSize   int             `json:"page_size"`
		TotalPages int             `json:"total_pages"`
	} `json:"data"`
}

// TaskListItem 任务列表 Item 参数
type TaskListItem struct {
	ID               uint              `json:"id"`
	TaskID           string            `json:"task_id"`
	OriginalFilename string            `json:"original_filename"`
	FileType         string            `json:"file_type"`
	Status           models.TaskStatus `json:"status"`
	ErrorMessage     string            `json:"error_message"`
	CreatedAt        string            `json:"created_at"`
	FinishedAt       string            `json:"finished_at"`
	UpdatedAt        string            `json:"updated_at"`
	OutputFileID     string            `json:"output_file_id,omitempty"`
	OutputFilePath   string            `json:"output_file_path,omitempty"`
	DownloadFileName string            `json:"download_file_name,omitempty"`
}

// TaskDeleteRequest 删除任务请求参数
type TaskDeleteRequest struct {
	TaskID uint `json:"task_id" binding:"required"`
}

// TaskDeleteResponse 删除任务响应参数
type TaskDeleteResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
