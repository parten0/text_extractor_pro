from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    job_id: str
    message: str
    file_count: int


class JobProgressResponse(BaseModel):
    """Real-time job progress data"""
    job_id: str
    status: JobStatus
    progress: float  # 0.0 to 1.0
    current_file: Optional[int] = None
    total_files: Optional[int] = None
    message: str
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    """Final results with download links"""
    job_id: str
    status: JobStatus
    csv_path: Optional[str] = None
    json_path: Optional[str] = None
    processed_files: int
    message: str
    error: Optional[str] = None


class JobListResponse(BaseModel):
    """List of all jobs"""
    jobs: List[Dict[str, Any]]
