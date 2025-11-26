package main

import (
	"context"
	"flow_test_engine/internal"
	"flow_test_engine/pkg/common"
	"log"
)

func main() {
	// 加载配置
	cfg, err := common.LoadConfig("")
	if err != nil {
		log.Fatalf("加载配置失败: %v", err)
	}

	// 初始化日志
	logger, err := common.InitLogger(&cfg.Log)
	if err != nil {
		log.Fatalf("初始化日志失败: %v", err)
	}
	defer logger.Sync()

	// 启动服务
	ctx := context.Background()
	if err := internal.Start(ctx, cfg); err != nil {
		log.Fatalf("启动服务失败: %v", err)
	}
}
