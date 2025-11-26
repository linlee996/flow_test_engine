package utils

import (
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

// UploadResult 上传结果
type UploadResult struct {
	OriginalName string
	FilePath     string
	FileType     string
	Size         int64
}

// SaveUploadedFile 保存上传的文件
func SaveUploadedFile(file *multipart.FileHeader, uploadDir string, logger *zap.Logger) (*UploadResult, error) {
	// 验证文件类型
	fileType := GetFileType(file.Filename)
	if !IsAllowedFileType(fileType) {
		logger.Warn("不支持的文件类型",
			zap.String("file_name", file.Filename),
			zap.String("file_type", fileType),
		)
		return nil, fmt.Errorf("unsupported file type: %s", fileType)
	}

	// 确保上传目录存在
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		logger.Error("创建上传目录失败",
			zap.String("upload_dir", uploadDir),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to create upload directory: %w", err)
	}

	// 生成唯一文件名
	ext := filepath.Ext(file.Filename)
	timestamp := time.Now().UnixMilli()
	newFilename := fmt.Sprintf("%s_%d%s", uuid.New().String(), timestamp, ext)
	filePath := filepath.Join(uploadDir, newFilename)

	// 打开上传的文件
	src, err := file.Open()
	if err != nil {
		logger.Error("打开上传文件失败",
			zap.String("file_name", file.Filename),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to open uploaded file: %w", err)
	}
	defer src.Close()

	// 创建目标文件
	dst, err := os.Create(filePath)
	if err != nil {
		logger.Error("创建目标文件失败",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to create destination file: %w", err)
	}
	defer dst.Close()

	// 复制文件内容
	size, err := dst.ReadFrom(src)
	if err != nil {
		logger.Error("复制文件内容失败",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to copy file content: %w", err)
	}

	logger.Info("文件保存成功",
		zap.String("original_name", file.Filename),
		zap.String("saved_path", filePath),
		zap.Int64("file_size", size),
	)

	return &UploadResult{
		OriginalName: file.Filename,
		FilePath:     filePath,
		FileType:     fileType,
		Size:         size,
	}, nil
}

// GetFileType 获取文件类型
func GetFileType(filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))
	switch ext {
	case ".pdf":
		return "pdf"
	case ".doc":
		return "doc"
	case ".docx":
		return "docx"
	case ".txt":
		return "txt"
	default:
		return "unknown"
	}
}

// IsAllowedFileType 检查是否为允许的文件类型
func IsAllowedFileType(fileType string) bool {
	allowedTypes := []string{"pdf", "doc", "docx", "txt"}
	for _, allowed := range allowedTypes {
		if fileType == allowed {
			return true
		}
	}
	return false
}

// DeleteFile 删除文件
func DeleteFile(filePath string, logger *zap.Logger) error {
	if filePath == "" {
		return nil
	}

	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil // 文件不存在，不需要删除
	}

	if err := os.Remove(filePath); err != nil {
		logger.Warn("删除文件失败",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return fmt.Errorf("failed to delete file: %w", err)
	}

	logger.Info("文件删除成功", zap.String("file_path", filePath))
	return nil
}

// FileExists 检查文件是否存在
func FileExists(filePath string) bool {
	_, err := os.Stat(filePath)
	return err == nil
}

// GetFileName 从文件路径中提取文件名
func GetFileName(filePath string) string {
	return filepath.Base(filePath)
}

// DownloadResult 下载结果
//
//
//
// DownloadResult 下载结果
type DownloadResult struct {
	OriginalName string
	FilePath     string
	FileType     string
	Size         int64
}

// DownloadFromResponse 从 HTTP 响应下载文件到本地
// outputDir: 输出目录
// outputFileName: 输出文件名（不包含扩展名）
// logger: 日志记录器
// resp: HTTP 响应
func DownloadFromResponse(outputDir string, outputFileName string, logger *zap.Logger, resp io.ReadCloser) (*DownloadResult, error) {
	defer resp.Close()

	// 确保输出目录存在
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		logger.Error("创建输出目录失败",
			zap.String("output_dir", outputDir),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to create output directory: %w", err)
	}

	// 生成输出文件名（添加 .xlsx 扩展名）
	fileName := fmt.Sprintf("%s.xlsx", outputFileName)
	filePath := filepath.Join(outputDir, fileName)

	// 创建输出文件
	outFile, err := os.Create(filePath)
	if err != nil {
		logger.Error("创建输出文件失败",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to create output file: %w", err)
	}
	defer outFile.Close()

	// 复制文件内容并计算大小
	size, err := io.Copy(outFile, resp)
	if err != nil {
		logger.Error("写入文件内容失败",
			zap.String("file_path", filePath),
			zap.Error(err),
		)
		return nil, fmt.Errorf("failed to write file content: %w", err)
	}

	logger.Info("文件下载成功",
		zap.String("file_path", filePath),
		zap.String("file_name", fileName),
		zap.Int64("file_size", size),
	)

	return &DownloadResult{
		OriginalName: fileName,
		FilePath:     filePath,
		FileType:     "xlsx",
		Size:         size,
	}, nil
}
