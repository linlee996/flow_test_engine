package api

import (
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/service"
	"github.com/gin-gonic/gin"
	"strconv"
)

type CaseTemplate interface {
	Create(c *gin.Context)
	Update(c *gin.Context)
	Delete(c *gin.Context)
	List(c *gin.Context)
}

type caseTemplate struct {
	svr service.CaseTemplateService
}

func NewCaseTemplate(svr service.CaseTemplateService) CaseTemplate {
	return &caseTemplate{svr: svr}
}

func (ct *caseTemplate) Create(c *gin.Context) {
	var req dto.CaseTemplateCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	if err := ct.svr.Create(c.Request.Context(), &req); err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "创建失败: " + err.Error(),
		})
		return
	}

	c.JSON(200, dto.CaseTemplateResponse{
		Code:    0,
		Message: "创建成功",
	})
}

func (ct *caseTemplate) Update(c *gin.Context) {
	var req dto.CaseTemplateUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "参数错误: " + err.Error(),
		})
		return
	}

	if err := ct.svr.Update(c.Request.Context(), &req); err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "更新失败: " + err.Error(),
		})
		return
	}

	c.JSON(200, dto.CaseTemplateResponse{
		Code:    0,
		Message: "更新成功",
	})
}

func (ct *caseTemplate) Delete(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseUint(idStr, 10, 64)
	if err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "参数错误",
		})
		return
	}

	if err := ct.svr.Delete(c.Request.Context(), uint(id)); err != nil {
		c.JSON(200, dto.CaseTemplateResponse{
			Code:    1,
			Message: "删除失败: " + err.Error(),
		})
		return
	}

	c.JSON(200, dto.CaseTemplateResponse{
		Code:    0,
		Message: "删除成功",
	})
}

func (ct *caseTemplate) List(c *gin.Context) {
	resp, err := ct.svr.List(c.Request.Context())
	if err != nil {
		c.JSON(200, dto.CaseTemplateListResponse{
			Code:    1,
			Message: "查询失败: " + err.Error(),
			Data:    []dto.CaseTemplateItem{},
		})
		return
	}

	c.JSON(200, resp)
}
