package dto

// UploadResponse 上传文件响应
type UploadResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    struct {
		FilePath   string `json:"file_path"`
		UploadFile string `json:"upload_file"`
	} `json:"data"`
}

// DownloadRequest 下载文件请求
type DownloadRequest struct {
	TaskID string `json:"task_id" binding:"required"`
}

// DownloadResponse 下载文件响应
type DownloadResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
