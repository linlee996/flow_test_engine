package errcodes

import (
	"errors"
	"fmt"
)

const serviceBaseCode = 1020

const (
	// ParameterErrorCode 参数错误
	ParameterErrorCode = iota + serviceBaseCode
	// UserNotLoginCode 用户未登录
	UserNotLoginCode
	// UserSessionExpiredCode 用户SESSION已过期
	UserSessionExpiredCode
	// DBErrorCode 数据库操作错误
	DBErrorCode
	// ProcessErrorCode 流程错误
	ProcessErrorCode
	// ThirdPartyErrorCode 三方接口错误
	ThirdPartyErrorCode
)

// global error codes
var (
	// ErrParameterErrorCode 参数错误
	ErrParameterErrorCode = errors.New(fmt.Sprintf("Parameter error, code: %d", ParameterErrorCode))
	// ErrUserNotLogin 用户未登录
	ErrUserNotLogin = errors.New(fmt.Sprintf("User not logged in, code: %d", UserNotLoginCode))
	// ErrUserSessionExpired 用户SESSION已过期
	ErrUserSessionExpired = errors.New(fmt.Sprintf("User SESSION has expired, code: %d", UserSessionExpiredCode))
)
