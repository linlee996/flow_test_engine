package service

import (
	"context"
	"errors"
	"flow_test_engine/internal/assemble"
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/errcodes"
	"flow_test_engine/internal/repo"
	"flow_test_engine/internal/repo/models"
	"flow_test_engine/pkg/common"
	"flow_test_engine/utils"
	"fmt"
	"go.uber.org/zap"
	"mime/multipart"
	"os"
	"path/filepath"
	"strconv"
)

type Task interface {
	TaskCreate(ctx context.Context, req *dto.TaskCreateRequest) (*dto.TaskCreateResponse, error)
	TaskList(ctx context.Context, req *dto.TaskListRequest) (*dto.TaskListResponse, error)
	TaskDelete(ctx context.Context, req *dto.TaskDeleteRequest) (*dto.TaskDeleteResponse, error)
	UploadFile(ctx context.Context, file interface{}) (*dto.UploadResponse, error)
	GetDownloadFile(ctx context.Context, taskID string) (string, string, error)
}

func NewTask(repo repo.Task, langflowService LangflowService, templateService CaseTemplateService, fileCfg common.FileConfig, logger *zap.Logger) Task {
	return &task{
		repo:            repo,
		langflowService: langflowService,
		templateService: templateService,
		logger:          logger,
		fileConfig:      fileCfg,
	}
}

type task struct {
	repo            repo.Task
	langflowService LangflowService
	templateService CaseTemplateService
	logger          *zap.Logger
	fileConfig      common.FileConfig
}

func (l *task) TaskCreate(ctx context.Context, req *dto.TaskCreateRequest) (*dto.TaskCreateResponse, error) {
	if req == nil {
		return nil, errcodes.ErrParameterErrorCode
	}

	// 请求类型转换
	com, err := assemble.TaskCreateReq2Model(ctx, req)
	if err != nil {
		return nil, err
	}

	// 创建任务记录
	if err = l.repo.Create(ctx, com); err != nil {
		return &dto.TaskCreateResponse{
			Code:    errcodes.ProcessErrorCode,
			Message: "保存任务记录失败: " + err.Error(),
		}, errors.New("保存任务记录失败: " + err.Error())
	}

	// 异步启动工作流
	go func() {
		var customPrompt *string
		if req.TemplateID != nil {
			prompt, err := l.templateService.BuildPromptWithTemplate(context.Background(), req.TemplateID, "./config/prompt.md")
			if err != nil {
				l.logger.Error("构建自定义 prompt 失败", zap.Error(err))
			} else {
				customPrompt = &prompt
			}
		}

		err = l.langflowService.RunWorkflow(context.Background(), com.ID, com.LocalFilePath, req.DownloadFile, customPrompt)
		if err != nil {
			// 更新任务状态为失败
			com.Status = models.TaskStatusFailed
			err = l.repo.Update(context.Background(), com)
			if err != nil {
				return
			}
		}
	}()

	return &dto.TaskCreateResponse{
		Code:    0,
		Message: "任务创建成功",
	}, nil
}

func (l *task) TaskList(ctx context.Context, req *dto.TaskListRequest) (*dto.TaskListResponse, error) {
	if req == nil {
		return nil, errcodes.ErrParameterErrorCode
	}

	query := assemble.TaskList2Query(ctx, req)

	tasks, total, err := l.repo.List(ctx, query)
	if err != nil {
		return nil, errors.New("任务列表查询失败: " + err.Error())
	}

	// 转换模型到 DTO
	items := assemble.TaskModelList2Dto(tasks)

	// 计算总页数
	pageSize := query.PageSize
	if pageSize <= 0 {
		pageSize = 20
	}
	totalPages := int((total + int64(pageSize) - 1) / int64(pageSize))

	resp := &dto.TaskListResponse{
		Code:    0,
		Message: "查询成功",
		Data: struct {
			List       []*dto.TaskListItem `json:"list"`
			Total      int64               `json:"total"`
			Page       int                 `json:"page"`
			PageSize   int                 `json:"page_size"`
			TotalPages int                 `json:"total_pages"`
		}{
			List:       items,
			Total:      total,
			Page:       query.Page,
			PageSize:   pageSize,
			TotalPages: totalPages,
		},
	}

	return resp, nil
}

func (l *task) TaskDelete(ctx context.Context, req *dto.TaskDeleteRequest) (*dto.TaskDeleteResponse, error) {
	if req == nil || req.TaskID == 0 {
		return nil, errcodes.ErrParameterErrorCode
	}

	// 获取任务信息
	taskModel, err := l.repo.GetById(ctx, req.TaskID)
	if err != nil {
		return &dto.TaskDeleteResponse{
			Code:    errcodes.ProcessErrorCode,
			Message: "获取任务信息失败: " + err.Error(),
		}, err
	}

	// 删除本地上传文件
	if taskModel.LocalFilePath != "" {
		if err := os.Remove(taskModel.LocalFilePath); err != nil && !os.IsNotExist(err) {
			l.logger.Warn("删除上传文件失败", zap.String("file_path", taskModel.LocalFilePath), zap.Error(err))
		}
	}

	// 删除本地输出文件
	if taskModel.OutputFile != "" {
		if err := os.Remove(taskModel.OutputFile); err != nil && !os.IsNotExist(err) {
			l.logger.Warn("删除输出文件失败", zap.String("file_path", taskModel.OutputFile), zap.Error(err))
		}
	}

	// 调用 Langflow API 删除上传文件
	if taskModel.UploadFileID != "" {
		if err := l.langflowService.DeleteFile(ctx, taskModel.UploadFileID); err != nil {
			l.logger.Warn("删除 Langflow 上传文件失败", zap.String("file_id", taskModel.UploadFileID), zap.Error(err))
		}
	}

	// 调用 Langflow API 删除输出文件
	if taskModel.OutputFileID != "" {
		if err := l.langflowService.DeleteFile(ctx, taskModel.OutputFileID); err != nil {
			l.logger.Warn("删除 Langflow 输出文件失败", zap.String("file_id", taskModel.OutputFileID), zap.Error(err))
		}
	}

	// 删除任务记录
	if err := l.repo.Delete(ctx, req.TaskID); err != nil {
		return &dto.TaskDeleteResponse{
			Code:    errcodes.ProcessErrorCode,
			Message: "删除任务失败: " + err.Error(),
		}, err
	}

	return &dto.TaskDeleteResponse{
		Code:    0,
		Message: "删除成功",
	}, nil
}

func (l *task) UploadFile(ctx context.Context, file interface{}) (*dto.UploadResponse, error) {
	fileHeader, ok := file.(*multipart.FileHeader)
	if !ok {
		return nil, errors.New("无效的文件类型")
	}

	// 使用 utils.SaveUploadedFile 保存文件
	result, err := utils.SaveUploadedFile(fileHeader, l.fileConfig.UploadDir, l.logger)
	if err != nil {
		return nil, err
	}

	resp := &dto.UploadResponse{
		Code:    0,
		Message: "上传成功",
	}
	resp.Data.FilePath = result.FilePath
	resp.Data.UploadFile = result.OriginalName

	return resp, nil
}

func (l *task) GetDownloadFile(ctx context.Context, taskID string) (string, string, error) {
	// 将 string 类型的 taskID 转换为 uint
	taskIDUint, err := strconv.ParseUint(taskID, 10, 64)
	if err != nil {
		return "", "", fmt.Errorf("无效的任务ID格式: %w", err)
	}

	// 从数据库获取任务记录
	taskModel, err := l.repo.GetById(ctx, uint(taskIDUint))
	if err != nil {
		return "", "", fmt.Errorf("获取任务记录失败: %w", err)
	}

	// 检查任务状态，只有完成状态的任务才能下载
	if taskModel.Status != models.TaskStatusFinished {
		if taskModel.Status == models.TaskStatusRunning {
			return "", "", errors.New("任务还在运行中，请稍后再试")
		}
		return "", "", fmt.Errorf("任务状态异常: %s", taskModel.Status)
	}

	// 检查是否有文件ID
	if taskModel.OutputFileID == "" {
		return "", "", errors.New("文件ID不存在，无法下载")
	}

	// 检查文件是否已经存在
	if taskModel.OutputFile != "" {
		if _, err = os.Stat(taskModel.OutputFile); err == nil {
			// 文件已存在，直接返回
			l.logger.Info("文件已存在，直接返回", zap.String("filePath", taskModel.OutputFile))
			return taskModel.OutputFile, filepath.Base(taskModel.OutputFile), nil
		}
	}

	// 文件不存在，需要重新下载
	// 使用 OutputFile（英文）作为临时文件名从 langflow 下载，然后重命名为 DownloadFile（中文）
	l.logger.Info("文件不存在，开始从Langflow下载并重命名",
		zap.String("file_id", taskModel.OutputFileID),
		zap.String("temp_file_name", taskModel.OutputFile),
		zap.String("final_file_name", taskModel.DownloadFile),
	)

	// 调用 langflowService 下载并重命名文件
	filePath, err := l.langflowService.DownloadWorkflowResult(ctx, taskModel.OutputFileID, taskModel.OutputFile, taskModel.DownloadFile)
	if err != nil {
		l.logger.Error("下载文件失败",
			zap.Error(err),
			zap.String("task_id", taskID),
			zap.String("file_id", taskModel.OutputFileID),
		)
		return "", "", fmt.Errorf("下载文件失败: %w", err)
	}

	// 更新数据库中的 OutputFile 字段为重命名后的路径
	taskModel.OutputFile = filePath
	if err = l.repo.Update(ctx, taskModel); err != nil {
		l.logger.Warn("更新文件路径到数据库失败", zap.Error(err), zap.String("file_path", filePath))
		// 不返回错误，因为文件已经成功下载和重命名
	}

	l.logger.Info("文件下载并重命名成功", zap.String("file_path", filePath))
	return filePath, filepath.Base(filePath), nil
}
