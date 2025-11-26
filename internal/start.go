package internal

import (
	"context"
	"flow_test_engine/internal/api"
	"flow_test_engine/internal/middleware"
	"flow_test_engine/internal/repo"
	"flow_test_engine/internal/repo/models"
	"flow_test_engine/internal/service"
	"flow_test_engine/pkg/common"
	"flow_test_engine/pkg/infrastructure"
	"fmt"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
	"gorm.io/gorm"
)

// InitDB 初始化数据库
func InitDB(cfg *common.Config, logger *zap.Logger) (*gorm.DB, error) {
	logger.Info("正在初始化SQLite连接...")

	// 创建数据库连接
	db, err := infrastructure.NewSQLiteClient(&cfg.SQLite)
	if err != nil {
		logger.Error("数据库连接失败", zap.Error(err))
		return nil, fmt.Errorf("数据库连接失败: %w", err)
	}

	logger.Info("数据库连接成功")

	// 自动迁移表结构
	logger.Info("正在执行数据库迁移...")
	if err := db.AutoMigrate(
		&models.Task{},
		&models.CaseTemplate{},
	); err != nil {
		logger.Error("数据库迁移失败", zap.Error(err))
		return nil, fmt.Errorf("数据库迁移失败: %w", err)
	}

	logger.Info("数据库迁移成功")
	return db, nil
}

// InitComponents 初始化应用组件
func InitComponents(db *gorm.DB, cfg *common.Config, logger *zap.Logger) (
	repo.Task,
	service.LangflowService,
	service.Task,
	service.CaseTemplateService,
	api.Task,
	api.CaseTemplate,
) {
	logger.Info("正在初始化应用组件...")

	// 初始化Repo层
	taskRepo := repo.NewTask(db)
	templateRepo := repo.NewCaseTemplate(db)

	// 初始化Service层
	langflowService := service.NewLangflowService(cfg.Custom, logger, cfg.File, taskRepo)
	templateService := service.NewCaseTemplateService(templateRepo, logger)
	taskService := service.NewTask(taskRepo, langflowService, templateService, cfg.File, logger)

	// 初始化API层
	taskAPI := api.NewTask(taskService)
	templateAPI := api.NewCaseTemplate(templateService)

	// 初始化默认模板
	if err := templateService.InitDefaultTemplate(context.Background(), "./config/prompt.md"); err != nil {
		logger.Warn("初始化默认模板失败", zap.Error(err))
	}

	logger.Info("应用组件初始化完成")
	return taskRepo, langflowService, taskService, templateService, taskAPI, templateAPI
}

// NewGinEngine 创建Gin引擎并注册路由
func NewGinEngine(
	cfg *common.Config,
	logger *zap.Logger,
	taskAPI api.Task,
	templateAPI api.CaseTemplate,
) *gin.Engine {
	logger.Info("正在初始化Gin引擎...")

	// 设置Gin模式
	if cfg.Mode == "release" {
		gin.SetMode(gin.ReleaseMode)
	}

	// 创建Gin引擎
	r := gin.New()

	// 注册全局中间件
	r.Use(gin.Recovery())
	r.Use(middleware.LoggerMiddleware(logger))
	r.Use(middleware.CORSMiddleware())

	// 注册路由
	RegisterRoutes(r, taskAPI, templateAPI, logger)

	// 添加静态文件服务
	r.Static("/static", "./static")

	// 根路径重定向到静态文件首页
	r.GET("/", func(c *gin.Context) {
		c.File("./static/index.html")
	})

	logger.Info("Gin引擎初始化完成")
	return r
}

// RegisterRoutes 注册API路由
func RegisterRoutes(
	r *gin.Engine,
	taskAPI api.Task,
	templateAPI api.CaseTemplate,
	logger *zap.Logger,
) {
	logger.Info("正在注册API路由...")

	// 健康检查
	r.GET("/ping", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"code":    0,
			"message": "pong",
		})
	})

	// v1版本API
	v1 := r.Group("/api/v1")
	{
		// 任务相关接口
		task := v1.Group("/task")
		{
			task.POST("/create", taskAPI.TaskCreate)
			task.GET("/list", taskAPI.TaskList)
			task.DELETE("/delete", taskAPI.TaskDelete)
		}

		// 兼容前端的任务接口
		tasks := v1.Group("/tasks")
		{
			tasks.GET("", taskAPI.TaskList)
			tasks.DELETE("/:taskId", taskAPI.TaskDeleteByTaskId)
		}

		// 文件相关接口
		upload := v1.Group("/upload")
		{
			upload.POST("", taskAPI.UploadFile)
		}

		// 下载接口
		v1.GET("/download/:taskId", taskAPI.DownloadFile)

		// 用例模板相关接口
		template := v1.Group("/templates")
		{
			template.POST("", templateAPI.Create)
			template.PUT("", templateAPI.Update)
			template.DELETE("/:id", templateAPI.Delete)
			template.GET("", templateAPI.List)
		}
	}

	logger.Info("API路由注册完成")
}

// Start 启动服务
func Start(ctx context.Context, cfg *common.Config) error {
	// 初始化日志
	logger, err := common.InitLogger(&cfg.Log)
	if err != nil {
		return fmt.Errorf("初始化日志失败: %w", err)
	}

	logger.Info("==================== 服务启动中 ====================")
	logger.Info("服务名称", zap.String("name", cfg.Name))
	logger.Info("运行模式", zap.String("mode", cfg.Mode))
	logger.Info("监听端口", zap.String("port", cfg.Port))

	// 初始化数据库
	db, err := InitDB(cfg, logger)
	if err != nil {
		return fmt.Errorf("初始化数据库失败: %w", err)
	}

	// 初始�组件
	_, _, _, _, taskAPI, templateAPI := InitComponents(db, cfg, logger)

	// 创建Gin引擎
	engine := NewGinEngine(cfg, logger, taskAPI, templateAPI)

	// 启动HTTP服务器
	addr := fmt.Sprintf(":%s", cfg.Port)
	logger.Info("服务启动成功", zap.String("address", addr))
	logger.Info("====================================================")

	if err := engine.Run(addr); err != nil {
		logger.Error("服务启动失败", zap.Error(err))
		return fmt.Errorf("服务启动失败: %w", err)
	}

	return nil
}
