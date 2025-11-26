package repo

import (
	"context"
	"flow_test_engine/internal/repo/models"
	"fmt"
	"gorm.io/gorm"
)

type TaskQuery struct {
	Page             int
	PageSize         int
	TaskID           uint
	Status           string
	OriginalFilename string
}

type Task interface {
	Create(ctx context.Context, task *models.Task) error
	Update(ctx context.Context, task *models.Task) error
	Delete(ctx context.Context, id uint) error
	GetById(ctx context.Context, id uint) (*models.Task, error)
	GetByTaskId(ctx context.Context, taskID string) (*models.Task, error)
	List(ctx context.Context, query *TaskQuery) ([]*models.Task, int64, error)
}

type task struct {
	db *gorm.DB
}

func NewTask(db *gorm.DB) Task {
	return &task{
		db: db,
	}
}

func (t *task) Create(ctx context.Context, task *models.Task) error {
	if err := t.db.WithContext(ctx).Create(task).Error; err != nil {
		return fmt.Errorf("failed to create task: %w", err)
	}
	return nil
}

func (t *task) Update(ctx context.Context, task *models.Task) error {
	if err := t.db.WithContext(ctx).Save(task).Error; err != nil {
		return fmt.Errorf("failed to update task: %w", err)
	}
	return nil
}

func (t *task) Delete(ctx context.Context, id uint) error {
	if err := t.db.WithContext(ctx).Delete(&models.Task{}, id).Error; err != nil {
		return fmt.Errorf("failed to delete task: %w", err)
	}
	return nil
}

func (t *task) GetById(ctx context.Context, id uint) (*models.Task, error) {
	var task models.Task
	if err := t.db.WithContext(ctx).First(&task, id).Error; err != nil {
		return nil, fmt.Errorf("failed to get task: %w", err)
	}
	return &task, nil
}

func (t *task) GetByTaskId(ctx context.Context, taskID string) (*models.Task, error) {
	var task models.Task
	if err := t.db.WithContext(ctx).Where("task_id = ?", taskID).First(&task).Error; err != nil {
		return nil, fmt.Errorf("failed to get task: %w", err)
	}
	return &task, nil
}

func (t *task) List(ctx context.Context, query *TaskQuery) ([]*models.Task, int64, error) {
	db := t.db.WithContext(ctx).Model(&models.Task{})

	if query.TaskID != 0 {
		db = db.Where("task_id = ?", query.TaskID)
	}

	if query.Status != "" {
		db = db.Where("status = ?", query.Status)
	}

	if query.OriginalFilename != "" {
		db = db.Where("original_filename LIKE ?", "%"+query.OriginalFilename+"%")
	}

	// 获取总数
	var total int64
	if err := db.Count(&total).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to count tasks: %w", err)
	}

	// 获取分页数据
	var tasks []*models.Task
	err := db.Order("created_at DESC").
		Limit(query.PageSize).
		Offset((query.Page - 1) * query.PageSize).
		Find(&tasks).Error

	return tasks, total, err
}
