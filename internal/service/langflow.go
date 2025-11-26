package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/repo"
	"flow_test_engine/internal/repo/models"
	"flow_test_engine/pkg/common"
	"flow_test_engine/utils"
	"fmt"
	"go.uber.org/zap"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type LangflowService interface {
	RunWorkflow(ctx context.Context, taskID uint, filePath, downloadFileName string, customPrompt *string) error
	HandleWorkflowCompletion(ctx context.Context, taskID uint) error
	DownloadWorkflowResult(ctx context.Context, fileID string, tempFileName string, finalFileName string) (string, error)
	DeleteFile(ctx context.Context, fileID string) error
}

func NewLangflowService(cfg common.CustomConfig, logger *zap.Logger, fileCfg common.FileConfig, repo repo.Task) LangflowService {
	return &langflowService{
		config:     cfg,
		logger:     logger,
		fileConfig: fileCfg,
		repo:       repo,
		client: &http.Client{
			Timeout: 20 * time.Minute,
		},
	}
}

type langflowService struct {
	config     common.CustomConfig
	logger     *zap.Logger
	client     *http.Client
	fileConfig common.FileConfig
	repo       repo.Task
}

// RunWorkflow 运行工作流（两步流程：先上传文件，再运行工作流，使用流式响应监控）
func (s *langflowService) RunWorkflow(ctx context.Context, taskID uint, filePath, downloadFileName string, customPrompt *string) error {
	s.logger.Info("[RunWorkflow] starting workflow execution",
		zap.Uint("task_id", taskID),
		zap.String("file_path", filePath),
		zap.String("download_file_name", downloadFileName),
	)

	// 上传文件到 Langflow
	langflowFilePath, uploadFileID, err := s.uploadFile(ctx, filePath)
	if err != nil {
		s.logger.Error("[RunWorkflow] failed to upload file to langflow",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return fmt.Errorf("failed to upload file: %w", err)
	}
	s.logger.Info("[RunWorkflow] file uploaded to langflow successfully",
		zap.Uint("task_id", taskID),
		zap.String("langflow_file_path", langflowFilePath),
		zap.String("upload_file_id", uploadFileID),
	)

	// 生成带时间戳的文件名
	timestamp := time.Now().UnixMilli()
	finalFileName := fmt.Sprintf("testcase_%v", timestamp)
	downloadFilePath := fmt.Sprintf("%s_%v", downloadFileName, timestamp)

	updateTask, err := s.repo.GetById(ctx, taskID)
	if err != nil {
		s.logger.Error("[RunWorkflow] failed to get task by ID",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return err
	}

	// 更新变量
	updateTask.FilePath = langflowFilePath
	updateTask.UploadFileID = uploadFileID
	updateTask.OutputFile = finalFileName
	updateTask.DownloadFile = downloadFilePath

	// 更新数据库字段
	if err = s.repo.Update(ctx, updateTask); err != nil {
		s.logger.Error("[RunWorkflow] failed to update task in database",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return err
	}

	// 使用 Langflow 文件路径运行工作流
	filePath = langflowFilePath

	// 构建工作流请求
	reqBody := &dto.LangflowRunRequest{
		InputType:  "text",
		InputValue: "根据需求文档生成测试用例",
		OutputType: "text",
	}

	// 如果配置了 File 组件 ID，使用 tweaks 参数传递文件路径
	if s.config.FileComponentID != "" {
		reqBody.Tweaks = map[string]interface{}{
			s.config.FileComponentID: map[string]interface{}{
				"path": langflowFilePath,
			},
			s.config.SaveFileComponentID: map[string]interface{}{
				"file_name": finalFileName,
			},
		}
		// 如果提供了自定义 prompt，添加到 tweaks
		if customPrompt != nil && s.config.PromptComponentID != "" {
			reqBody.Tweaks[s.config.PromptComponentID] = map[string]interface{}{
				"template": *customPrompt,
			}
		}
	} else {
		return fmt.Errorf("")
	}

	requestBody, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	// 构建运行工作流URL (使用stream=true启用流式响应)
	url := fmt.Sprintf("%s%s%s?stream=true", s.config.BaseURL, s.config.RunEndpoint, s.config.FlowID)

	s.logger.Info("Calling workflow API", zap.String("url", url), zap.String("requestBody", string(requestBody)))

	// 创建HTTP请求
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(requestBody))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// 设置请求头
	req.Header.Set("Content-Type", "application/json")
	if s.config.APIKey != "" {
		req.Header.Set("x-api-key", s.config.APIKey)
	}

	// 发送请求
	resp, err := s.client.Do(req)
	if err != nil {
		s.logger.Error("Failed to send workflow request",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return fmt.Errorf("failed to send request: %w", err)
	}

	// 检查状态码
	if resp.StatusCode != http.StatusOK {
		defer resp.Body.Close()
		responseBody, _ := io.ReadAll(resp.Body)
		s.logger.Error("Workflow API error",
			zap.Uint("task_id", taskID),
			zap.Int("status_code", resp.StatusCode),
			zap.String("response_body", string(responseBody)),
		)
		return fmt.Errorf("run workflow API error (status %d): %s", resp.StatusCode, string(responseBody))
	}
	s.logger.Info("Workflow API call successful",
		zap.Uint("task_id", taskID),
		zap.Int("status_code", resp.StatusCode),
	)

	// 启动异步流式监控（响应体将在 goroutine 中关闭）
	go s.monitorWorkflowStatus(ctx, taskID, resp)

	return nil
}

// uploadFile 上传文件到Langflow文件上传端点
func (s *langflowService) uploadFile(ctx context.Context, filePath string) (string, string, error) {
	s.logger.Info("[uploadFile] starting file upload",
		zap.String("file_path", filePath),
	)
	// 创建multipart form数据
	var requestBody bytes.Buffer
	writer := multipart.NewWriter(&requestBody)

	// 添加文件
	file, err := os.Open(filePath)
	if err != nil {
		return "", "", fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	fileWriter, err := writer.CreateFormFile("file", filepath.Base(filePath))
	if err != nil {
		return "", "", fmt.Errorf("failed to create form file: %w", err)
	}

	_, err = io.Copy(fileWriter, file)
	if err != nil {
		return "", "", fmt.Errorf("failed to copy file: %w", err)
	}

	writer.Close()

	// 构建文件上传URL
	url := s.config.BaseURL + s.config.FileEndpoint
	s.logger.Info("Uploading file", zap.String("url", url), zap.String("file_path", filePath))

	// 创建HTTP请求
	req, err := http.NewRequestWithContext(ctx, "POST", url, &requestBody)
	if err != nil {
		return "", "", fmt.Errorf("failed to create request: %w", err)
	}

	// 设置请求头
	req.Header.Set("Content-Type", writer.FormDataContentType())
	if s.config.APIKey != "" {
		req.Header.Set("x-api-key", s.config.APIKey)
	}

	// 发送请求
	resp, err := s.client.Do(req)
	if err != nil {
		s.logger.Error("Failed to upload file",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return "", "", fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	// 读取响应
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", "", fmt.Errorf("failed to read response: %w", err)
	}

	// 接受 200 OK 或 201 Created
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		s.logger.Error("File upload API error",
			zap.String("file_path", filePath),
			zap.Int("status_code", resp.StatusCode),
			zap.String("response_body", string(responseBody)),
		)
		return "", "", fmt.Errorf("file upload API error (status %d): %s", resp.StatusCode, string(responseBody))
	}

	s.logger.Info("File upload successful", zap.Int("status_code", resp.StatusCode), zap.String("response_body", string(responseBody)))

	// 解析响应
	var uploadResponse dto.LangflowFileUploadResponse
	err = json.Unmarshal(responseBody, &uploadResponse)
	if err != nil {
		s.logger.Error("Failed to parse upload response", zap.Error(err), zap.String("response_body", string(responseBody)))
		return "", "", fmt.Errorf("failed to parse response: %w", err)
	}

	return uploadResponse.FilePath, uploadResponse.FileID, nil
}

// monitorWorkflowStatus 监控工作流状态
func (s *langflowService) monitorWorkflowStatus(ctx context.Context, taskID uint, resp *http.Response) {
	s.logger.Info("[monitorWorkflowStatus] starting workflow monitoring",
		zap.Uint("task_id", taskID),
		zap.Int("status_code", resp.StatusCode),
	)
	defer func(Body io.ReadCloser) {
		err := Body.Close()
		if err != nil {

		}
	}(resp.Body)

	// 设置30分钟超时
	timeout := time.NewTimer(30 * time.Minute)
	defer timeout.Stop()

	// 创建通道接收解析结果
	eventChan := make(chan *dto.LangflowStreamEvent)
	errorChan := make(chan error)

	// 获取任务信息
	taskModel, err := s.repo.GetById(ctx, taskID)
	if err != nil {
		s.logger.Error("[monitorWorkflowStatus] failed to get task by ID",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return
	}

	// 启动goroutine读取流式响应
	go func() {
		scanner := bufio.NewScanner(resp.Body)
		lineNum := 0
		for scanner.Scan() {
			lineNum++
			line := strings.TrimSpace(scanner.Text())

			// 跳过空行
			if line == "" {
				continue
			}

			s.logger.Debug("Received stream line",
				zap.Uint("task_id", taskID),
				zap.Int("line_num", lineNum),
				zap.String("line", line),
			)

			// 尝试解析JSON事件
			var event dto.LangflowStreamEvent
			if err := json.Unmarshal([]byte(line), &event); err != nil {
				// 如果无法解析，记录日志但继续
				s.logger.Warn("Failed to parse stream event",
					zap.Uint("task_id", taskID),
					zap.Error(err),
					zap.String("line", line),
				)
				continue
			}

			s.logger.Debug("Parsed stream event successfully",
				zap.Uint("task_id", taskID),
				zap.String("event", event.Event),
				zap.Any("data", event.Data),
			)

			// 发送事件到通道
			eventChan <- &event
		}

		// 检查扫描器错误
		if err = scanner.Err(); err != nil {
			s.logger.Error("Stream scanner error",
				zap.Uint("task_id", taskID),
				zap.Error(err),
			)
			errorChan <- fmt.Errorf("stream reading error: %w", err)
		}
		close(eventChan)
		close(errorChan)
	}()

	// 处理事件
	for {
		select {
		case event := <-eventChan:
			if event == nil {
				// 通道关闭，流结束但没有收到 end 事件
				s.logger.Error("[monitorWorkflowStatus] channel closed, stream ended but no end event received",
					zap.Uint("task_id", taskID),
				)
				taskModel.Status = models.TaskStatusFailed
				taskModel.ErrorMessage = fmt.Sprintf("Channel closed, stream ended but no end event received")
				err = s.repo.Update(ctx, taskModel)
				if err != nil {
					s.logger.Error("[monitorWorkflowStatus] failed to update task status on channel close",
						zap.Uint("task_id", taskID),
						zap.Error(err),
					)
					return
				}
				return
			}

			s.logger.Info("Received workflow event",
				zap.Uint("task_id", taskID),
				zap.String("event", event.Event),
				zap.Any("event_data", event.Data),
			)

			// 检查事件类型
			switch event.Event {
			case "end":
				// 工作流完成
				s.logger.Info("Workflow completed successfully",
					zap.Uint("task_id", taskID),
					zap.Any("event_data", event.Data),
				)

				// 如果有输出文件名，尝试获取文件 ID
				if taskModel.OutputFile != "" {
					fileID, err := s.findFileIDByName(taskModel.OutputFile)
					if err != nil {
						s.logger.Error("[monitorWorkflowStatus] failed to find file ID by name",
							zap.Uint("task_id", taskID),
							zap.String("file_name", taskModel.OutputFile),
							zap.Error(err),
						)
						taskModel.Status = models.TaskStatusFailed
						err = s.repo.Update(ctx, taskModel)
						if err != nil {
							s.logger.Error("[monitorWorkflowStatus] failed to update task status",
								zap.Uint("task_id", taskID),
								zap.Error(err),
							)
							return
						}
						return
					}

					// 保存文件 ID
					taskModel.OutputFileID = fileID
					err = s.repo.Update(ctx, taskModel)
					if err != nil {
						s.logger.Error("[monitorWorkflowStatus] failed to update task with file ID",
							zap.Uint("task_id", taskID),
							zap.String("file_id", fileID),
							zap.Error(err),
						)
						return
					}

					s.logger.Info("Saved output file ID successfully",
						zap.Uint("task_id", taskID),
						zap.String("file_id", fileID),
					)
				}

				// 标记任务为完成
				now := time.Now()
				taskModel.Status = models.TaskStatusFinished
				taskModel.FinishedAt = &now
				err = s.repo.Update(ctx, taskModel)
				if err != nil {
					s.logger.Error("[monitorWorkflowStatus] failed to update task status to finished",
						zap.Uint("task_id", taskID),
						zap.Error(err),
					)
					return
				}
				return

			case "error":
				// 工作流失败
				errorMsg := "Workflow execution failed"
				if data, ok := event.Data["error"].(string); ok {
					errorMsg = data
				}
				s.logger.Error("Workflow execution failed",
					zap.Uint("task_id", taskID),
					zap.String("error_message", errorMsg),
				)
				taskModel.ErrorMessage = errorMsg
				taskModel.Status = models.TaskStatusFailed
				err = s.repo.Update(ctx, taskModel)
				if err != nil {
					s.logger.Error("[monitorWorkflowStatus] failed to update task status on error",
						zap.Uint("task_id", taskID),
						zap.String("error_message", errorMsg),
						zap.Error(err),
					)
					return
				}
				return

			default:
				// 未接收事件，继续监听
				continue
			}

		case err := <-errorChan:
			if err != nil {
				s.logger.Error("Error reading stream for task",
					zap.Uint("task_id", taskID),
					zap.Error(err),
				)
				s.logger.Error("[monitorWorkflowStatus] failed to update task status on stream error",
					zap.Uint("task_id", taskID),
					zap.Error(err),
				)
				taskModel.Status = models.TaskStatusFailed
				taskModel.ErrorMessage = "Error reading stream for task"
				err = s.repo.Update(ctx, taskModel)
				if err != nil {
					s.logger.Error("[monitorWorkflowStatus] failed to update task status",
						zap.Uint("task_id", taskID),
						zap.Error(err),
					)
					return
				}
				return
			}

		case <-timeout.C:
			// 超时
			s.logger.Error("Workflow execution timeout",
				zap.Uint("task_id", taskID),
				zap.String("error_message", "Workflow execution timeout"),
			)
			taskModel.Status = models.TaskStatusFailed
			taskModel.ErrorMessage = "Workflow execution timeout"
			err = s.repo.Update(ctx, taskModel)
			if err != nil {
				s.logger.Error("[monitorWorkflowStatus] failed to update task status on timeout",
					zap.Uint("task_id", taskID),
					zap.Error(err),
				)
			}
			return
		}
	}
}

// HandleWorkflowCompletion 处理工作流完成
func (s *langflowService) HandleWorkflowCompletion(ctx context.Context, taskID uint) error {
	s.logger.Info("[HandleWorkflowCompletion] starting workflow completion handling",
		zap.Uint("task_id", taskID),
	)

	// 获取任务记录，得到输出文件名
	t, err := s.repo.GetById(ctx, taskID)
	if err != nil {
		s.logger.Error("[HandleWorkflowCompletion] failed to get task by ID",
			zap.Uint("task_id", taskID),
			zap.Error(err),
		)
		return fmt.Errorf("failed to get task record: %w", err)
	}

	// 使用 OutputFile（英文文件名）从 langflow 下载，避免中文问题
	// 下载后的文件会使用 DownloadFile（用户指定的名称）进行重命名
	finalFilePath, err := s.DownloadWorkflowResult(ctx, t.OutputFileID, t.OutputFile, t.DownloadFile)
	if err != nil {
		s.logger.Error("[HandleWorkflowCompletion] failed to download and rename workflow result",
			zap.Uint("task_id", taskID),
			zap.String("output_file_id", t.OutputFileID),
			zap.String("output_file", t.OutputFile),
			zap.String("download_file", t.DownloadFile),
			zap.Error(err),
		)
		return fmt.Errorf("failed to download result: %w", err)
	}

	// 更新数据库中的 OutputFile 字段为重命名后的文件路径
	t.OutputFile = finalFilePath
	err = s.repo.Update(ctx, t)
	if err != nil {
		s.logger.Error("[HandleWorkflowCompletion] failed to update task with final file path",
			zap.Uint("task_id", taskID),
			zap.String("final_file_path", finalFilePath),
			zap.Error(err),
		)
		// 不返回错误，因为文件已经成功下载和重命名
	}

	s.logger.Info("Task completed successfully",
		zap.Uint("task_id", taskID),
		zap.String("output_file", t.OutputFile),
		zap.String("download_file", t.DownloadFile),
	)

	return nil
}

// DownloadWorkflowResult 下载工作流结果
// tempFileName: 用于从 langflow 下载的临时文件名（必须是英文，因为 langflow 端点不支持中文）
// finalFileName: 下载完成后重命名的最终文件名（可以是中文，用户下载时使用）
func (s *langflowService) DownloadWorkflowResult(ctx context.Context, fileID string, tempFileName string, finalFileName string) (string, error) {
	s.logger.Info("[DownloadWorkflowResult] starting file download",
		zap.String("file_id", fileID),
		zap.String("temp_file_name", tempFileName),
		zap.String("final_file_name", finalFileName),
		zap.String("output_dir", s.fileConfig.OutputDir),
	)
	url := s.config.BaseURL + s.config.FileEndpoint + fileID

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		s.logger.Error("[DownloadWorkflowResult] failed to create HTTP request",
			zap.String("file_id", fileID),
			zap.String("temp_file_name", tempFileName),
			zap.String("final_file_name", finalFileName),
			zap.Error(err),
		)
		return "", err
	}

	if s.config.APIKey != "" {
		req.Header.Set("x-api-key", s.config.APIKey)
	}
	req.Header.Set("accept", "application/json")

	httpResp, err := s.client.Do(req)
	if err != nil {
		s.logger.Error("[DownloadWorkflowResult] failed to send HTTP request",
			zap.String("file_id", fileID),
			zap.String("temp_file_name", tempFileName),
			zap.String("final_file_name", finalFileName),
			zap.Error(err),
		)
		return "", err
	}

	if httpResp.StatusCode != http.StatusOK {
		responseBody, readErr := io.ReadAll(httpResp.Body)
		if readErr != nil {
			s.logger.Warn("Failed to read error response body",
				zap.String("file_id", fileID),
				zap.Error(readErr),
			)
			responseBody = []byte("failed to read response body")
		}
		if closeErr := httpResp.Body.Close(); closeErr != nil {
			s.logger.Warn("Failed to close response body",
				zap.String("file_id", fileID),
				zap.Error(closeErr),
			)
		}
		s.logger.Error("[DownloadWorkflowResult] download failed with non-OK status",
			zap.String("file_id", fileID),
			zap.String("temp_file_name", tempFileName),
			zap.String("final_file_name", finalFileName),
			zap.Int("status_code", httpResp.StatusCode),
			zap.String("response_body", string(responseBody)),
		)
		return "", fmt.Errorf("download error (status %d): %s", httpResp.StatusCode, string(responseBody))
	}

	// 步骤1: 使用临时文件名（英文）从 langflow 下载
	tempResult, err := utils.DownloadFromResponse(s.fileConfig.OutputDir, tempFileName, s.logger, httpResp.Body)
	if err != nil {
		s.logger.Error("[DownloadWorkflowResult] failed to download temp file from response",
			zap.String("file_id", fileID),
			zap.String("temp_file_name", tempFileName),
			zap.String("final_file_name", finalFileName),
			zap.String("output_dir", s.fileConfig.OutputDir),
			zap.Error(err),
		)
		return "", fmt.Errorf("failed to download temp file: %w", err)
	}

	s.logger.Info("Temp file downloaded successfully",
		zap.String("file_id", fileID),
		zap.String("temp_file_path", tempResult.FilePath),
		zap.String("temp_file_name", tempFileName),
	)

	// 步骤2: 重命名为最终的文件名（支持中文）
	finalFileNameWithExt := fmt.Sprintf("%s.xlsx", finalFileName)
	finalFilePath := filepath.Join(s.fileConfig.OutputDir, finalFileNameWithExt)

	// 检查最终的文件是否已经存在，如果存在则删除（避免重命名失败）
	if _, err := os.Stat(finalFilePath); err == nil {
		s.logger.Warn("Final file already exists, removing old file",
			zap.String("final_file_path", finalFilePath),
		)
		if err := os.Remove(finalFilePath); err != nil {
			s.logger.Error("[DownloadWorkflowResult] failed to remove existing final file",
				zap.String("final_file_path", finalFilePath),
				zap.Error(err),
			)
		}
	}

	// 执行重命名
	if err := os.Rename(tempResult.FilePath, finalFilePath); err != nil {
		s.logger.Error("[DownloadWorkflowResult] failed to rename temp file to final file",
			zap.String("temp_file_path", tempResult.FilePath),
			zap.String("final_file_path", finalFilePath),
			zap.String("temp_file_name", tempFileName),
			zap.String("final_file_name", finalFileName),
			zap.Error(err),
		)
		// 尝试清理临时文件
		if removeErr := os.Remove(tempResult.FilePath); removeErr != nil {
			s.logger.Warn("Failed to remove temp file after rename error",
				zap.String("temp_file_path", tempResult.FilePath),
				zap.Error(removeErr),
			)
		}
		return "", fmt.Errorf("failed to rename file from %s to %s: %w", tempResult.FilePath, finalFilePath, err)
	}

	s.logger.Info("File renamed successfully",
		zap.String("file_id", fileID),
		zap.String("temp_file_name", tempFileName),
		zap.String("final_file_name", finalFileName),
		zap.String("final_file_path", finalFilePath),
	)

	return finalFilePath, nil
}

// getFileList 获取 Langflow 文件列表
func (s *langflowService) getFileList() ([]dto.LangflowFileInfo, error) {
	s.logger.Info("[getFileList] starting to get file list from langflow")
	url := s.config.BaseURL + s.config.FileEndpoint

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// 设置请求头
	req.Header.Set("accept", "application/json")
	if s.config.APIKey != "" {
		req.Header.Set("x-api-key", s.config.APIKey)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer func(Body io.ReadCloser) {
		err = Body.Close()
		if err != nil {

		}
	}(resp.Body)

	if resp.StatusCode != http.StatusOK {
		responseBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("get file list API error (status %d): %s", resp.StatusCode, string(responseBody))
	}

	var files []dto.LangflowFileInfo
	if err = json.NewDecoder(resp.Body).Decode(&files); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return files, nil
}

// findFileIDByName 根据文件名查找文件 ID
func (s *langflowService) findFileIDByName(fileName string) (string, error) {
	s.logger.Info("[findFileIDByName] starting to find file ID by name",
		zap.String("file_name", fileName),
	)
	files, err := s.getFileList()
	if err != nil {
		return "", fmt.Errorf("failed to get file list: %w", err)
	}

	// 遍历文件列表，查找匹配的文件名
	for _, file := range files {
		if file.Name == fileName {
			return file.ID, nil
		}
	}

	return "", fmt.Errorf("file not found: %s", fileName)
}

// DeleteFile 删除 Langflow 中的文件
func (s *langflowService) DeleteFile(ctx context.Context, fileID string) error {
	if fileID == "" {
		return nil
	}

	url := s.config.BaseURL + s.config.FileEndpoint + fileID
	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("accept", "application/json")
	if s.config.APIKey != "" {
		req.Header.Set("x-api-key", s.config.APIKey)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		responseBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("delete file API error (status %d): %s", resp.StatusCode, string(responseBody))
	}

	s.logger.Info("File deleted from Langflow", zap.String("file_id", fileID))
	return nil
}
