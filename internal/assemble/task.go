package assemble

import (
	"context"
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/errcodes"
	"flow_test_engine/internal/repo"
	"flow_test_engine/internal/repo/models"
	"flow_test_engine/utils"
	"strconv"
)

func TaskCreateReq2Model(_ context.Context, req *dto.TaskCreateRequest) (*models.Task, error) {
	if req.DownloadFile == "" || req.FilePath == "" {
		return nil, errcodes.ErrParameterErrorCode
	}
	return &models.Task{
		OriginalFilename: req.UploadFile,
		LocalFilePath:    req.FilePath,
		Status:           models.TaskStatusRunning,
		DownloadFile:     req.DownloadFile,
	}, nil
}

func TaskList2Query(_ context.Context, req *dto.TaskListRequest) *repo.TaskQuery {

	if req.Page < 1 {
		req.Page = 1
	}
	if req.PageSize < 1 || req.PageSize > 100 {
		req.PageSize = 20
	}

	return &repo.TaskQuery{
		TaskID:           req.TaskID,
		Status:           req.Status,
		OriginalFilename: req.OriginalFilename,
		Page:             req.Page,
		PageSize:         req.PageSize,
	}
}

// TaskModelList2Dto 将 models.Task 列表转换为 dto.TaskListItem 列表
func TaskModelList2Dto(tasks []*models.Task) []*dto.TaskListItem {
	if len(tasks) == 0 {
		return []*dto.TaskListItem{}
	}

	items := make([]*dto.TaskListItem, 0, len(tasks))
	for _, task := range tasks {
		items = append(items, TaskModel2Dto(task))
	}
	return items
}

// TaskModel2Dto 将单个 models.Task 转换为 dto.TaskListItem
func TaskModel2Dto(task *models.Task) *dto.TaskListItem {
	return &dto.TaskListItem{
		ID:               task.ID,
		TaskID:           strconv.FormatUint(uint64(task.ID), 10),
		OriginalFilename: task.OriginalFilename,
		FileType:         utils.GetFileType(task.LocalFilePath),
		Status:           task.Status,
		ErrorMessage:     task.ErrorMessage,
		CreatedAt:        utils.FormatTime(task.CreatedAt),
		FinishedAt:       utils.FormatTimePtr(task.FinishedAt),
		UpdatedAt:        utils.FormatTime(task.UpdatedAt),
		OutputFileID:     task.OutputFileID,
		OutputFilePath:   task.OutputFile,
		DownloadFileName: task.DownloadFile,
	}
}
