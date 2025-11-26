-- 创建数据库
CREATE DATABASE IF NOT EXISTS flow_test DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE flow_test;

-- 创建任务表
CREATE TABLE IF NOT EXISTS `task` (
    `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `original_filename` varchar(255) NOT NULL DEFAULT '' COMMENT '原始文件名',
    `file_path` varchar(500) NOT NULL DEFAULT '' COMMENT '上传文件路径',
    `status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '任务状态[0.运行中;1.任务完成;2.任务失败]',
    `langflow_run_id` varchar(255) DEFAULT '' COMMENT 'Langflow运行ID',
    `output_file` varchar(500) DEFAULT '' COMMENT '输出Excel文件名称',
    `download_file` varchar(500) DEFAULT '' COMMENT '下载Excel文件名称',
    `output_file_id` varchar(255) DEFAULT '' COMMENT 'Langflow输出文件ID',
    `error_message` text COMMENT '错误信息',
    `finished_at` datetime DEFAULT NULL COMMENT '完成时间',
    `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_status` (`status`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_task_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流任务表';

-- 插入测试数据（可选）
-- INSERT INTO `task` (original_filename, file_path, status, download_file) VALUES
-- ('测试需求文档.pdf', '/uploads/test.pdf', 1, '测试用例.xlsx');
