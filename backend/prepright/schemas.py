from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str
    weather_sensitivity: float = 1.0


class CategoryRead(CategoryCreate):
    id: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    weather_sensitivity: Optional[float] = None


class IngredientCreate(BaseModel):
    name: str
    unit: str = "units"


class IngredientRead(IngredientCreate):
    id: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    active: Optional[bool] = None


class ProductAliasCreate(BaseModel):
    alias_name: str


class ProductAliasRead(ProductAliasCreate):
    id: int

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    ingredient_id: int
    quantity_per_unit: float


class RecipeRead(BaseModel):
    id: int
    ingredient_id: int
    quantity_per_unit: float
    ingredient_name: str

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    category_id: int
    margin_pct: float = 0.0
    aliases: Optional[List[ProductAliasCreate]] = []
    recipes: Optional[List[RecipeCreate]] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    margin_pct: Optional[float] = None
    active: Optional[bool] = None
    aliases: Optional[List[ProductAliasCreate]] = None
    recipes: Optional[List[RecipeCreate]] = None


class ProductRead(BaseModel):
    id: int
    name: str
    category_id: int
    category_name: Optional[str]
    margin_pct: float
    active: bool
    created_at: datetime
    aliases: List[ProductAliasRead]
    recipes: List[RecipeRead]

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    date: str
    name: str
    impact_factor: float = 0.0


class EventUpdate(BaseModel):
    date: Optional[str] = None
    name: Optional[str] = None
    impact_factor: Optional[float] = None


class EventRead(EventCreate):
    id: int

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str


class ReceiptTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    active: bool = True
    source_keyword: Optional[str] = None
    line_pattern: str
    product_name_group: str = "name"
    quantity_group: str = "qty"
    price_group: str = "price"
    line_prefix: Optional[str] = None
    line_suffix: Optional[str] = None
    name_normalize: Optional[str] = None
    config: Optional[str] = None


class ReceiptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    source_keyword: Optional[str] = None
    line_pattern: Optional[str] = None
    product_name_group: Optional[str] = None
    quantity_group: Optional[str] = None
    price_group: Optional[str] = None
    line_prefix: Optional[str] = None
    line_suffix: Optional[str] = None
    name_normalize: Optional[str] = None
    config: Optional[str] = None


class ReceiptTemplateRead(ReceiptTemplateCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductMatch(BaseModel):
    product_id: int
    product_name: str
    matched_name: str
    quantity: float
    price: Optional[float] = None
    confidence: str = "medium"


class ReceiptProcessRequest(BaseModel):
    text: str
    template_name: Optional[str] = None


class SalesRecordRead(BaseModel):
    id: int
    product_id: int
    quantity: float
    sale_date: str
    source_template: Optional[str]
    confidence: str
    product_name: str

    class Config:
        from_attributes = True
