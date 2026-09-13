"""Pydantic input schemas shared by HRMS tools."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ListDoctypesInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	category: Optional[str] = Field(
		default=None,
		description="Optional category filter (e.g. 'Core HR', 'Attendance', 'Leave', 'Payroll', 'Recruitment')",
	)


class SchemaInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="Exact Frappe DocType name, e.g. 'Employee', 'Leave Application'")


class LinkOptionsInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	target_doctype: str = Field(
		...,
		description="The DocType a Link field points to (e.g. 'Department', 'Leave Type', 'Company', 'Branch')",
	)
	search: Optional[str] = Field(default=None, description="Optional substring to filter valid values")
	limit: int = Field(default=25, ge=1, le=100, description="Max options to return")


class ListDocsInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="Frappe DocType name, e.g. 'Employee', 'Leave Application'")
	fields: Optional[list[str]] = Field(
		default=None,
		description="Fields to return, e.g. ['name', 'employee_name', 'status']. Defaults to standard fields.",
	)
	filters: Optional[list[list[Any]] | dict[str, Any]] = Field(
		default=None,
		description='Filters e.g. [["status", "=", "Open"], ["employee", "=", "HR-EMP-00001"]]',
	)
	order_by: Optional[str] = Field(default=None, description="Sort order, e.g. 'creation desc'")
	limit: int = Field(default=20, ge=1, le=200, description="Max rows to return")
	offset: int = Field(default=0, ge=0, description="Pagination offset")


class GetDocInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name")
	name: str = Field(..., description="Document primary key ID, e.g. 'HR-EMP-00001'")


class CreateDocInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name, e.g. 'Employee', 'Salary Structure'")
	fields: dict[str, Any] = Field(
		...,
		description="Field values for new document. Use frappe_get_doctype_schema first to verify field names.",
	)


class UpdateDocInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name")
	name: str = Field(..., description="Document name/ID to update")
	fields: dict[str, Any] = Field(..., description="Key-value pairs to update on the document")


class DeleteDocInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name")
	name: str = Field(..., description="Document primary key ID to permanently delete")


class BulkCreateInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name, e.g. 'Department', 'Designation', 'Employee'")
	documents: list[dict[str, Any]] = Field(
		..., description="List of document field dictionaries to create in sequence"
	)


class GetAttendanceInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	employee: str = Field(..., description="Employee ID, e.g. 'HR-EMP-00001'")
	from_date: str = Field(..., description="Start date (YYYY-MM-DD)")
	to_date: str = Field(..., description="End date (YYYY-MM-DD)")


class MarkAttendanceInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	employee: str = Field(..., description="Employee ID, e.g. 'HR-EMP-00001'")
	attendance_date: str = Field(..., description="Date (YYYY-MM-DD)")
	status: Literal["Present", "Absent", "Half Day", "On Leave"] = Field(
		..., description="Attendance status to mark"
	)
	working_hours: Optional[float] = Field(default=None, description="Working hours completed")


class LeaveBalanceInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	employee: str = Field(..., description="Employee ID, e.g. 'HR-EMP-00001'")
	date: Optional[str] = Field(default=None, description="Date to check balance as of (YYYY-MM-DD). Defaults to today.")


class ApplyLeaveInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	employee: str = Field(..., description="Employee ID, e.g. 'HR-EMP-00001'")
	leave_type: str = Field(..., description="e.g. 'Casual Leave', 'Sick Leave', 'Privilege Leave'")
	from_date: str = Field(..., description="Start date (YYYY-MM-DD)")
	to_date: str = Field(..., description="End date (YYYY-MM-DD)")
	reason: Optional[str] = Field(default=None, description="Reason for leave request")
	half_day: bool = Field(default=False, description="Whether this is a half-day leave")
	half_day_date: Optional[str] = Field(default=None, description="Date of half-day if applicable (YYYY-MM-DD)")


class FindEmployeeInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	query: str = Field(
		...,
		description="Search term matching employee name, ID, email, or department (e.g. 'Jane', 'HR-EMP-00001')",
	)
	status: Optional[str] = Field(default="Active", description="Filter by status ('Active', 'Left', or None for all)")
	limit: int = Field(default=15, ge=1, le=50)


class SalarySlipsInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	employee: Optional[str] = Field(default=None, description="Filter by Employee ID, e.g. 'HR-EMP-00001'")
	start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
	end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
	limit: int = Field(default=12, ge=1, le=50)


class VerifyHRDatasetInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	from_date: str = Field(..., description="Start date for attendance and leave usage (YYYY-MM-DD)")
	to_date: str = Field(..., description="End date for attendance and leave usage (YYYY-MM-DD)")
	employee_filter: Optional[str] = Field(
		default=None,
		description="Optional substring to restrict verification to test employees or a team",
	)
	limit: int = Field(default=200, ge=1, le=500)


class DocActionInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name (e.g. 'Leave Application', 'Salary Slip')")
	name: str = Field(..., description="Document primary key ID")


class HistoryInput(BaseModel):
	model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
	doctype: str = Field(..., description="DocType name")
	name: str = Field(..., description="Document primary key ID")
