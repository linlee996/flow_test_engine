package repo

import (
	"context"
	"flow_test_engine/internal/repo/models"
	"fmt"
	"gorm.io/gorm"
)

type CaseTemplate interface {
	Create(ctx context.Context, template *models.CaseTemplate) error
	Update(ctx context.Context, template *models.CaseTemplate) error
	Delete(ctx context.Context, id uint) error
	GetByID(ctx context.Context, id uint) (*models.CaseTemplate, error)
	List(ctx context.Context) ([]*models.CaseTemplate, error)
	GetDefault(ctx context.Context) (*models.CaseTemplate, error)
}

type caseTemplate struct {
	db *gorm.DB
}

func NewCaseTemplate(db *gorm.DB) CaseTemplate {
	return &caseTemplate{db: db}
}

func (r *caseTemplate) Create(ctx context.Context, template *models.CaseTemplate) error {
	return r.db.WithContext(ctx).Create(template).Error
}

func (r *caseTemplate) Update(ctx context.Context, template *models.CaseTemplate) error {
	return r.db.WithContext(ctx).Save(template).Error
}

func (r *caseTemplate) Delete(ctx context.Context, id uint) error {
	return r.db.WithContext(ctx).Delete(&models.CaseTemplate{}, id).Error
}

func (r *caseTemplate) GetByID(ctx context.Context, id uint) (*models.CaseTemplate, error) {
	var template models.CaseTemplate
	if err := r.db.WithContext(ctx).First(&template, id).Error; err != nil {
		return nil, fmt.Errorf("failed to get template: %w", err)
	}
	return &template, nil
}

func (r *caseTemplate) List(ctx context.Context) ([]*models.CaseTemplate, error) {
	var templates []*models.CaseTemplate
	if err := r.db.WithContext(ctx).Order("is_default DESC, created_at DESC").Find(&templates).Error; err != nil {
		return nil, fmt.Errorf("failed to list templates: %w", err)
	}
	return templates, nil
}

func (r *caseTemplate) GetDefault(ctx context.Context) (*models.CaseTemplate, error) {
	var template models.CaseTemplate
	if err := r.db.WithContext(ctx).Where("is_default = ?", true).First(&template).Error; err != nil {
		return nil, fmt.Errorf("failed to get default template: %w", err)
	}
	return &template, nil
}
