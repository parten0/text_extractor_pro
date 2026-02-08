import os
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from api.models import (
    FileUploadResponse,
    JobProgressResponse,
    JobResultResponse,
    JobListResponse,
    JobStatus
)
from api.job_manager import job_manager


router = APIRouter(prefix="/api")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple PDF files and start processing job
    """
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Check all files are PDFs
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are allowed."
            )
    
    # Create job
    job_id = job_manager.create_job(files)
    
    # Update status to uploading
    job_manager.update_job_status(job_id, JobStatus.UPLOADING, "Uploading files")
    
    # Save files
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    try:
        # Get job upload directory
        job_upload_dir = job_manager.uploads_dir / job_id
        
        for i, file in enumerate(files):
            # Construct file path
            file_path = job_upload_dir / file.filename
            
            # Read and save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Update progress
            job_manager.update_job_progress(job_id, i + 1, len(files))
        
        # Start background processing
        background_tasks.add_task(job_manager.process_job, job_id)
        
        return FileUploadResponse(
            job_id=job_id,
            message="Files uploaded successfully. Processing started.",
            file_count=len(files)
        )
    
    except Exception as e:
        job_manager.set_job_error(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/jobs/{job_id}/status", response_model=JobProgressResponse)
async def get_job_status(job_id: str):
    """
    Get current job status and progress
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobProgressResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_file=job.current_file,
        total_files=job.total_files,
        message=job.message,
        error=job.error
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """
    Get job result with download information
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        csv_path=job.csv_path,
        json_path=job.json_path,
        processed_files=job.total_files,
        message=job.message,
        error=job.error
    )


@router.get("/jobs/{job_id}/download/csv")
async def download_csv(job_id: str):
    """
    Download CSV results for a job
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.csv_path or not os.path.exists(job.csv_path):
        raise HTTPException(status_code=404, detail="CSV file not found")
    
    return FileResponse(
        job.csv_path,
        media_type="text/csv",
        filename=f"extraction_results_{job_id}.csv"
    )


@router.get("/jobs/{job_id}/download/json")
async def download_json(job_id: str):
    """
    Download JSON results for a job
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.json_path or not os.path.exists(job.json_path):
        raise HTTPException(status_code=404, detail="JSON file not found")
    
    return FileResponse(
        job.json_path,
        media_type="application/json",
        filename=f"extraction_results_{job_id}.json"
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    """
    List all jobs (for debugging)
    """
    jobs = job_manager.get_all_jobs()
    return JobListResponse(jobs=jobs)
