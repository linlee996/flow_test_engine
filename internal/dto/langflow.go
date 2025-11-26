package dto

// LangflowRunRequest Langflow运行请求
type LangflowRunRequest struct {
	InputValue string                 `json:"input_value"`
	InputType  string                 `json:"input_type"`
	OutputType string                 `json:"output_type"`
	Tweaks     map[string]interface{} `json:"tweaks,omitempty"`
}

// LangflowStreamEvent Langflow流式事件响应
type LangflowStreamEvent struct {
	Event string                 `json:"event"`
	Data  map[string]interface{} `json:"data,omitempty"`
}

// LangflowFileUploadResponse Langflow文件上传响应
type LangflowFileUploadResponse struct {
	FileID   string `json:"id"`
	FilePath string `json:"path"`
}

// LangflowFileInfo Langflow文件信息
type LangflowFileInfo struct {
	ID       string  `json:"id"`
	Name     string  `json:"name"`
	Path     string  `json:"path"`
	Size     int64   `json:"size"`
	Provider *string `json:"provider"`
}
