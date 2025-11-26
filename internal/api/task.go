package api

import (
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/service"
	"github.com/gin-gonic/gin"
	"strconv"
)

type Task interface {
	TaskCreate(c *gin.Context)
	TaskList(c *gin.Context)
	TaskDelete(c *gin.Context)
	TaskDeleteByTaskId(c *gin.Context)
	UploadFile(c *gin.Context)
	DownloadFile(c *gin.Context)
}

func NewTask(svr service.Task) Task {
	return &task{
		svr: svr,
	}
}

type task struct {
	svr service.Task
}

func (obj *task) TaskCreate(ctx *gin.Context) {
	req := &dto.TaskCreateRequest{}
	err := ctx.ShouldBindJSON(&req)
	if err != nil {
		// TODO: 处理错误
		ctx.JSON(200, dto.TaskCreateResponse{
			Code:    1,
			Message: "参数错误",
			Data: struct {
				TaskID string `json:"task_id"`
				Status string `json:"status"`
			}{},
		})
		return
	}

	// 调用服务
	resp, err := obj.svr.TaskCreate(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(200, dto.TaskCreateResponse{
			Code:    1,
			Message: err.Error(),
			Data: struct {
				TaskID string `json:"task_id"`
				Status string `json:"status"`
			}{},
		})
		return
	}

	ctx.JSON(200, resp)
}

func (obj *task) TaskList(ctx *gin.Context) {
	req := &dto.TaskListRequest{}
	if err := ctx.ShouldBindQuery(req); err != nil {
		ctx.JSON(200, dto.TaskListResponse{
			Code:    1,
			Message: "参数错误: " + err.Error(),
			Data: struct {
				List       []*dto.TaskListItem `json:"list"`
				Total      int64               `json:"total"`
				Page       int                 `json:"page"`
				PageSize   int                 `json:"page_size"`
				TotalPages int                 `json:"total_pages"`
			}{},
		})
		return
	}

	resp, err := obj.svr.TaskList(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(200, dto.TaskListResponse{
			Code:    1,
			Message: "查询失败: " + err.Error(),
			Data: struct {
				List       []*dto.TaskListItem `json:"list"`
				Total      int64               `json:"total"`
				Page       int                 `json:"page"`
				PageSize   int                 `json:"page_size"`
				TotalPages int                 `json:"total_pages"`
			}{},
		})
		return
	}

	ctx.JSON(200, resp)
}

func (obj *task) TaskDelete(ctx *gin.Context) {
	req := &dto.TaskDeleteRequest{}
	if err := ctx.ShouldBindJSON(req); err != nil {
		ctx.JSON(200, dto.TaskDeleteResponse{
			Code:    1,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	resp, err := obj.svr.TaskDelete(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(200, dto.TaskDeleteResponse{
			Code:    1,
			Message: "删除失败: " + err.Error(),
		})
		return
	}

	ctx.JSON(200, resp)
}

func (obj *task) TaskDeleteByTaskId(ctx *gin.Context) {
	taskId := ctx.Param("taskId")
	if taskId == "" {
		ctx.JSON(200, dto.TaskDeleteResponse{
			Code:    1,
			Message: "任务ID不能为空",
		})
		return
	}

	id, err := strconv.ParseUint(taskId, 10, 64)
	if err != nil {
		ctx.JSON(200, dto.TaskDeleteResponse{
			Code:    1,
			Message: "任务ID格式错误",
		})
		return
	}

	req := &dto.TaskDeleteRequest{TaskID: uint(id)}
	resp, err := obj.svr.TaskDelete(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(200, dto.TaskDeleteResponse{
			Code:    1,
			Message: "删除失败: " + err.Error(),
		})
		return
	}

	ctx.JSON(200, resp)
}

func (obj *task) UploadFile(ctx *gin.Context) {
	file, err := ctx.FormFile("file")
	if err != nil {
		ctx.JSON(200, dto.UploadResponse{
			Code:    1,
			Message: "文件上传失败: " + err.Error(),
		})
		return
	}

	resp, err := obj.svr.UploadFile(ctx.Request.Context(), file)
	if err != nil {
		ctx.JSON(200, dto.UploadResponse{
			Code:    1,
			Message: "文件上传失败: " + err.Error(),
		})
		return
	}

	ctx.JSON(200, resp)
}

func (obj *task) DownloadFile(ctx *gin.Context) {
	taskId := ctx.Param("taskId")
	if taskId == "" {
		ctx.JSON(200, gin.H{
			"code":    1,
			"message": "任务ID不能为空",
		})
		return
	}

	filePath, fileName, err := obj.svr.GetDownloadFile(ctx.Request.Context(), taskId)
	if err != nil {
		ctx.JSON(200, gin.H{
			"code":    1,
			"message": "获取文件失败: " + err.Error(),
		})
		return
	}

	ctx.FileAttachment(filePath, fileName)
}
