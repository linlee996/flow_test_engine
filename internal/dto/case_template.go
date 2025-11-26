package dto

type CaseTemplateField struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

type CaseTemplateCreateRequest struct {
	Name   string               `json:"name" binding:"required"`
	Fields []CaseTemplateField  `json:"fields" binding:"required,min=1"`
}

type CaseTemplateUpdateRequest struct {
	ID     uint                 `json:"id" binding:"required"`
	Name   string               `json:"name" binding:"required"`
	Fields []CaseTemplateField  `json:"fields" binding:"required,min=1"`
}

type CaseTemplateListResponse struct {
	Code    int                  `json:"code"`
	Message string               `json:"message"`
	Data    []CaseTemplateItem   `json:"data"`
}

type CaseTemplateItem struct {
	ID        uint                 `json:"id"`
	Name      string               `json:"name"`
	Fields    []CaseTemplateField  `json:"fields"`
	IsDefault bool                 `json:"is_default"`
	IsSystem  bool                 `json:"is_system"`
	CreatedAt string               `json:"created_at"`
	UpdatedAt string               `json:"updated_at"`
}

type CaseTemplateResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
