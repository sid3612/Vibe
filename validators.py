"""
Validation models and parsers for profile data
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re
import json
from datetime import datetime, timedelta

class SalaryInfo(BaseModel):
    """Salary range validation"""
    min_salary: float = Field(gt=0)
    max_salary: float = Field(gt=0)
    currency: str = Field(min_length=1, max_length=10)
    period: str = Field(pattern=r'^(month|year)$')
    
    @validator('max_salary')
    def max_must_be_greater_than_min(cls, v, values):
        if 'min_salary' in values and v < values['min_salary']:
            raise ValueError('Максимальная зарплата должна быть больше минимальной')
        return v

class ProfileData(BaseModel):
    """Complete profile validation"""
    # Required fields
    role: str = Field(min_length=1, max_length=100)
    current_location: str = Field(min_length=1, max_length=100)
    target_location: str = Field(min_length=1, max_length=100)
    level: str = Field(min_length=1, max_length=50)
    deadline_weeks: int = Field(ge=1, le=52)
    
    # Optional fields
    role_synonyms: Optional[List[str]] = Field(default=None, max_items=4)
    salary_info: Optional[SalaryInfo] = None
    company_types: Optional[List[str]] = Field(default=None, max_items=10)
    industries: Optional[List[str]] = Field(default=None, max_items=3)
    competencies: Optional[List[str]] = Field(default=None, max_items=10)
    superpowers: Optional[List[str]] = Field(default=None, min_items=3, max_items=5)
    constraints_text: Optional[str] = Field(default=None, max_length=500)

def parse_salary_string(salary_str: str) -> Optional[SalaryInfo]:
    """Parse salary string like '3000-5000 EUR/month'"""
    if not salary_str or salary_str.strip() == '':
        return None
    
    # Pattern: min-max currency/period or min-max currency period
    pattern = r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s+([A-Z]{3}|[$€£¥₽])\s*[/\s]*\s*(month|year)'
    match = re.search(pattern, salary_str, re.IGNORECASE)
    
    if not match:
        raise ValueError('Формат: 3000-5000 EUR/month или 3000-5000 USD year')
    
    min_sal, max_sal, currency, period = match.groups()
    
    return SalaryInfo(
        min_salary=float(min_sal),
        max_salary=float(max_sal),
        currency=currency.upper(),
        period=period.lower()
    )

def parse_list_input(input_str: str, max_items: int = 10) -> List[str]:
    """Parse comma-separated list with validation"""
    if not input_str or input_str.strip() == '':
        return []
    
    items = [item.strip() for item in input_str.split(',')]
    items = [item for item in items if item]  # Remove empty items
    
    if len(items) > max_items:
        raise ValueError(f'Максимум {max_items} элементов')
    
    # Check for duplicates
    if len(items) != len(set(items)):
        raise ValueError('Элементы не должны повторяться')
    
    return items

def calculate_target_end_date(weeks: int) -> str:
    """Calculate target end date from current date + N weeks"""
    today = datetime.now().date()
    target_date = today + timedelta(weeks=weeks)
    return target_date.strftime('%Y-%m-%d')

def validate_superpowers(superpowers_list: List[str]) -> bool:
    """Validate superpowers format: action → business effect"""
    if not superpowers_list or len(superpowers_list) < 3 or len(superpowers_list) > 5:
        return False
    
    for power in superpowers_list:
        # Should contain some indicator of business effect
        if not any(word in power.lower() for word in ['сэкономил', 'заработал', 'ускорил', 'увеличил', 'снизил', 'улучшил']):
            return False
    
    return True