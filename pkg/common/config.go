package common

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/natefinch/lumberjack"
	"github.com/spf13/viper"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Config 全局配置结构
type Config struct {
	Name   string       `mapstructure:"name"`
	Mode   string       `mapstructure:"mode"`
	Port   string       `mapstructure:"port"`
	Log    LogConfig    `mapstructure:"log"`
	SQLite SQLiteConfig `mapstructure:"sqlite"`
	File   FileConfig   `mapstructure:"file"`
	Custom CustomConfig `mapstructure:"langflow"`
}

// LogConfig 日志配置
type LogConfig struct {
	StorageLocation       string `mapstructure:"storageLocation"`
	RotationTime          int    `mapstructure:"rotationTime"`          // 日志轮换周期（小时）
	RemainRotationCount   int    `mapstructure:"remainRotationCount"` // 保留的日志文件数
	RemainLogLevel        int    `mapstructure:"remainLogLevel"`       // 日志级别: 3=error, 4=warn, 5=info, 6=debug
	IsStdout              bool   `mapstructure:"isStdout"`
	IsJson                bool   `mapstructure:"isJson"`
}

// SQLiteConfig SQLite 配置
type SQLiteConfig struct {
	DBPath       string `mapstructure:"db_path"`
	MaxOpenConns int    `mapstructure:"max_open_conns"`
	MaxIdleConns int    `mapstructure:"max_idle_conns"`
	MaxLifetime  int    `mapstructure:"max_lifetime"` // 连接可复用的最大时间（秒）
	LogLevel     string `mapstructure:"log_level"`    // 日志级别: debug, info, warn, error
}

// DSN 返回 SQLite 连接字符串
func (s *SQLiteConfig) DSN() string {
	return s.DBPath
}

// FileConfig 文件配置
type FileConfig struct {
	MaxFileSize int64  `mapstructure:"max_file_size"` // bytes
	UploadDir   string `mapstructure:"upload_dir"`
	OutputDir   string `mapstructure:"output_dir"`
}

// CustomConfig Langflow 自定义配置
type CustomConfig struct {
	BaseURL             string `mapstructure:"base_url"`
	RunEndpoint         string `mapstructure:"flow_run_endpoint"`
	FileEndpoint        string `mapstructure:"file_endpoint"`
	FlowID              string `mapstructure:"flow_id"`
	APIKey              string `mapstructure:"api_key"`
	FileComponentID     string `mapstructure:"file_component_id"`
	SaveFileComponentID string `mapstructure:"file_save_component_id"`
	PromptComponentID   string `mapstructure:"prompt_component_id"`
}

// LoadConfig 加载配置文件
func LoadConfig(configPath string) (*Config, error) {
	if configPath == "" {
		configPath = "./config/config.yaml"
	}

	// 检查配置文件是否存在
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("配置文件不存在: %s", configPath)
	}

	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	// 读取配置文件
	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("读取配置文件失败: %w", err)
	}

	var config Config
	if err := v.Unmarshal(&config); err != nil {
		return nil, fmt.Errorf("解析配置文件失败: %w", err)
	}

	// 环境变量覆盖（优先级：环境变量 > 配置文件）
	if langflowAPIKey := os.Getenv("LANGFLOW_API_KEY"); langflowAPIKey != "" {
		config.Custom.APIKey = langflowAPIKey
	}

	return &config, nil
}

// InitLogger 初始化日志
func InitLogger(cfg *LogConfig) (*zap.Logger, error) {
	// 解析日志级别
	var logLevel zapcore.Level
	switch cfg.RemainLogLevel {
	case 3:
		logLevel = zapcore.ErrorLevel
	case 4:
		logLevel = zapcore.WarnLevel
	case 5:
		logLevel = zapcore.InfoLevel
	case 6:
		logLevel = zapcore.DebugLevel
	default:
		logLevel = zapcore.InfoLevel
	}

	// 创建编码器配置
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.TimeKey = "timestamp"
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder
	encoderConfig.EncodeCaller = zapcore.ShortCallerEncoder
	encoderConfig.EncodeDuration = zapcore.StringDurationEncoder
	encoderConfig.EncodeName = zapcore.FullNameEncoder

	// 根据配置选择编码器
	var encoder zapcore.Encoder
	if cfg.IsJson {
		encoder = zapcore.NewJSONEncoder(encoderConfig)
	} else {
		encoder = zapcore.NewConsoleEncoder(encoderConfig)
	}

	// 创建核心写入器
	var cores []zapcore.Core

	// 标准输出
	if cfg.IsStdout {
		stdoutCore := zapcore.NewCore(encoder, zapcore.Lock(os.Stdout), logLevel)
		cores = append(cores, stdoutCore)
	} else {
		// 文件输出（带日志轮转）
		if cfg.StorageLocation == "" {
			cfg.StorageLocation = "./logs/"
		}

		// 创建日志目录
		if err := os.MkdirAll(cfg.StorageLocation, 0755); err != nil {
			return nil, fmt.Errorf("创建日志目录失败: %w", err)
		}

		// 主日志文件
		logPath := filepath.Join(cfg.StorageLocation, "app.log")

		// 配置 lumberjack 日志轮转
		lumberjackLogger := &lumberjack.Logger{
			Filename:   logPath,
			MaxSize:    100, // MB
			MaxAge:     cfg.RotationTime * 24, // 转换为天数
			MaxBackups: cfg.RemainRotationCount,
			Compress:   true, // 压缩旧日志
		}

		fileCore := zapcore.NewCore(encoder, zapcore.AddSync(lumberjackLogger), logLevel)
		cores = append(cores, fileCore)
	}

	// 创建并返回 logger
	core := zapcore.NewTee(cores...)
	logger := zap.New(core, zap.AddCaller(), zap.AddCallerSkip(1))

	return logger, nil
}
