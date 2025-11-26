package service

import (
	"context"
	"errors"
	"flow_test_engine/internal/dto"
	"flow_test_engine/internal/repo"
	"flow_test_engine/internal/repo/models"
	"flow_test_engine/utils"
	"fmt"
	"go.uber.org/zap"
	"os"
	"regexp"
	"strings"
)

type CaseTemplateService interface {
	Create(ctx context.Context, req *dto.CaseTemplateCreateRequest) error
	Update(ctx context.Context, req *dto.CaseTemplateUpdateRequest) error
	Delete(ctx context.Context, id uint) error
	List(ctx context.Context) (*dto.CaseTemplateListResponse, error)
	GetByID(ctx context.Context, id uint) (*models.CaseTemplate, error)
	InitDefaultTemplate(ctx context.Context, promptPath string) error
	BuildPromptWithTemplate(ctx context.Context, templateID *uint, basePromptPath string) (string, error)
}

type caseTemplateService struct {
	repo   repo.CaseTemplate
	logger *zap.Logger
}

func NewCaseTemplateService(repo repo.CaseTemplate, logger *zap.Logger) CaseTemplateService {
	return &caseTemplateService{
		repo:   repo,
		logger: logger,
	}
}

func (s *caseTemplateService) Create(ctx context.Context, req *dto.CaseTemplateCreateRequest) error {
	content := s.buildTemplateContent(req.Fields)
	template := &models.CaseTemplate{
		Name:    req.Name,
		Content: content,
	}
	return s.repo.Create(ctx, template)
}

func (s *caseTemplateService) Update(ctx context.Context, req *dto.CaseTemplateUpdateRequest) error {
	template, err := s.repo.GetByID(ctx, req.ID)
	if err != nil {
		return err
	}
	if template.IsSystem {
		return errors.New("系统模板不可修改")
	}
	template.Name = req.Name
	template.Content = s.buildTemplateContent(req.Fields)
	return s.repo.Update(ctx, template)
}

func (s *caseTemplateService) Delete(ctx context.Context, id uint) error {
	template, err := s.repo.GetByID(ctx, id)
	if err != nil {
		return err
	}
	if template.IsSystem {
		return errors.New("系统模板不可删除")
	}
	return s.repo.Delete(ctx, id)
}

func (s *caseTemplateService) List(ctx context.Context) (*dto.CaseTemplateListResponse, error) {
	templates, err := s.repo.List(ctx)
	if err != nil {
		return nil, err
	}

	items := make([]dto.CaseTemplateItem, 0, len(templates))
	for _, t := range templates {
		fields := s.parseTemplateContent(t.Content)
		items = append(items, dto.CaseTemplateItem{
			ID:        t.ID,
			Name:      t.Name,
			Fields:    fields,
			IsDefault: t.IsDefault,
			IsSystem:  t.IsSystem,
			CreatedAt: utils.FormatTime(t.CreatedAt),
			UpdatedAt: utils.FormatTime(t.UpdatedAt),
		})
	}

	return &dto.CaseTemplateListResponse{
		Code:    0,
		Message: "查询成功",
		Data:    items,
	}, nil
}

func (s *caseTemplateService) GetByID(ctx context.Context, id uint) (*models.CaseTemplate, error) {
	return s.repo.GetByID(ctx, id)
}

func (s *caseTemplateService) buildTemplateContent(fields []dto.CaseTemplateField) string {
	var lines []string
	for i, field := range fields {
		lines = append(lines, fmt.Sprintf("%d. **%s**：%s", i+1, field.Name, field.Description))
	}
	return strings.Join(lines, "\n")
}

func (s *caseTemplateService) parseTemplateContent(content string) []dto.CaseTemplateField {
	var fields []dto.CaseTemplateField
	re := regexp.MustCompile(`\d+\.\s+\*\*(.+?)\*\*[：:]\s*(.+)`)
	matches := re.FindAllStringSubmatch(content, -1)
	for _, match := range matches {
		if len(match) == 3 {
			fields = append(fields, dto.CaseTemplateField{
				Name:        match[1],
				Description: match[2],
			})
		}
	}
	return fields
}

// InitDefaultTemplate 初始化默认模板
func (s *caseTemplateService) InitDefaultTemplate(ctx context.Context, promptPath string) error {
	// 检查是否已存在默认模板
	_, err := s.repo.GetDefault(ctx)
	if err == nil {
		s.logger.Info("默认模板已存在，跳过初始化")
		return nil
	}

	// 读取 prompt.md 文件
	content, err := os.ReadFile(promptPath)
	if err != nil {
		return fmt.Errorf("读取 prompt 文件失败: %w", err)
	}

	// 提取 3.3 节的模板内容
	templateContent := s.extractTemplateSection(string(content))
	if templateContent == "" {
		return errors.New("未找到模板内容")
	}

	// 创建默认模板
	template := &models.CaseTemplate{
		Name:      "默认模板",
		Content:   templateContent,
		IsDefault: true,
		IsSystem:  true,
	}

	return s.repo.Create(ctx, template)
}

func (s *caseTemplateService) extractTemplateSection(content string) string {
	// 提取 ### 3.3 测试用例输出格式 部分的字段列表
	re := regexp.MustCompile(`(?s)测试用例表格数据中每个测试用例必须且仅包含以下字段：\s*\n\n((?:\d+\.\s+\*\*.*?\*\*：.*?\n)+)`)
	matches := re.FindStringSubmatch(content)
	if len(matches) > 1 {
		return strings.TrimSpace(matches[1])
	}
	return ""
}

// BuildPromptWithTemplate 根据模板构建完整的 prompt
func (s *caseTemplateService) BuildPromptWithTemplate(ctx context.Context, templateID *uint, basePromptPath string) (string, error) {
	// 读取基础 prompt
	baseContent, err := os.ReadFile(basePromptPath)
	if err != nil {
		return "", fmt.Errorf("读取基础 prompt 失败: %w", err)
	}

	var template *models.CaseTemplate
	if templateID != nil {
		template, err = s.repo.GetByID(ctx, *templateID)
		if err != nil {
			return "", fmt.Errorf("获取模板失败: %w", err)
		}
	} else {
		template, err = s.repo.GetDefault(ctx)
		if err != nil {
			return "", fmt.Errorf("获取默认模板失败: %w", err)
		}
	}

	// 替换模板部分
	prompt := string(baseContent)
	re := regexp.MustCompile(`(?s)(测试用例表格数据中每个测试用例必须且仅包含以下字段：\s*\n\n)(?:\d+\.\s+\*\*.*?\*\*：.*?\n)+`)
	prompt = re.ReplaceAllString(prompt, fmt.Sprintf("${1}%s\n", template.Content))

	return prompt, nil
}
