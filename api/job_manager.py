import os
import uuid
import shutil
import json
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from threading import Lock
from pathlib import Path

from api.models import JobStatus
from core.extractor_service import ExtractorService


class Job:
    """Represents a single processing job"""
    
    def __init__(self, job_id: str, total_files: int):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.current_file = 0
        self.total_files = total_files
        self.message = "Job created"
        self.error: Optional[str] = None
        self.csv_path: Optional[str] = None
        self.json_path: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Serialize job to dictionary for JSON storage"""
        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'progress': self.progress,
            'current_file': self.current_file,
            'total_files': self.total_files,
            'message': self.message,
            'error': self.error,
            'csv_path': self.csv_path,
            'json_path': self.json_path,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        """Deserialize job from dictionary"""
        # Handle backward compatibility: old format had file_paths, new format has total_files
        if 'total_files' in data:
            total_files = data['total_files']
        elif 'file_paths' in data:
            # Old format - calculate total_files from file_paths length
            total_files = len(data['file_paths'])
        else:
            # Fallback
            total_files = 0
        
        job = cls(data['job_id'], total_files)
        job.status = JobStatus(data['status'])
        job.progress = data['progress']
        job.current_file = data['current_file']
        job.message = data['message']
        job.error = data.get('error')
        job.csv_path = data.get('csv_path')
        job.json_path = data.get('json_path')
        job.created_at = datetime.fromisoformat(data['created_at'])
        job.completed_at = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        return job


class JobManager:
    """Manages background jobs for document processing"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.lock = Lock()  # Using regular Lock, _save_state won't acquire it
        
        # Setup directories
        project_root = Path(__file__).parent.parent
        self.uploads_dir = project_root / "uploads"
        self.outputs_dir = project_root / "outputs"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup state file
        self.state_file = project_root / "job_state.json"
        
        # Load existing state from file
        self._load_state()
    
    def create_job(self, files: list) -> str:
        """Create a new job and return job ID"""
        job_id = str(uuid.uuid4())
        
        # Create job-specific upload directory
        job_upload_dir = self.uploads_dir / job_id
        job_upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded files and count them
        total_files = len(files)
        for file in files:
            file_path = job_upload_dir / file.filename
            # Save file logic here (handled by routes.py)
        
        # Create job with total file count
        job = Job(job_id, total_files)
        
        with self.lock:
            self.jobs[job_id] = job
            self._save_state()  # Save state after creating job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus, message: str = ""):
        """Update job status"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = status
                if message:
                    self.jobs[job_id].message = message
                self._save_state()  # Save state after status update
    
    def update_job_progress(self, job_id: str, current: int, total: int):
        """Update job progress"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.current_file = current
                job.total_files = total
                job.progress = current / total if total > 0 else 0.0
                job.message = f"Processing file {current} of {total}"
                self._save_state()  # Save state after progress update
    
    def set_job_error(self, job_id: str, error: str):
        """Set job error"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = error
                job.message = "Processing failed"
                job.completed_at = datetime.now()
                self._save_state()  # Save state after error
    
    def set_job_complete(self, job_id: str, csv_path: str, json_path: str):
        """Mark job as complete"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.csv_path = csv_path
                job.json_path = json_path
                job.message = "Processing completed successfully"
                job.completed_at = datetime.now()
                self._save_state()  # Save state after completion
                job.progress = 1.0
    
    def process_job(self, job_id: str):
        """Process a job in the background"""
        job = self.get_job(job_id)
        if not job:
            return
        
        job_upload_dir = None
        job_invoices_dir = None
        
        try:
            # Update status to processing
            self.update_job_status(job_id, JobStatus.PROCESSING, "Starting document processing")
            
            # Create job-specific output directory
            job_output_dir = self.outputs_dir / job_id
            job_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Move uploaded files to a temporary invoices folder structure
            job_upload_dir = self.uploads_dir / job_id
            job_invoices_dir = job_upload_dir / "invoices_temp"
            job_invoices_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files to invoices subfolder (ExtractorService expects subfolders)
            batch_folder = job_invoices_dir / "batch"
            batch_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy all PDF files from upload directory to batch folder
            for pdf_file in job_upload_dir.glob("*.pdf"):
                shutil.copy(pdf_file, batch_folder / pdf_file.name)
            
            # Create progress callback
            def progress_callback(current: int, total: int):
                self.update_job_progress(job_id, current, total)
            
            # Initialize ExtractorService with custom output location
            service = ExtractorService(
                str(job_invoices_dir),
                progress_callback=progress_callback
            )
            
            # Override output folders to use job-specific directory (no subfolders)
            service.outputs_folder = str(job_output_dir)
            service.json_folder = str(job_output_dir)
            service.csv_folder = str(job_output_dir)
            # No need to create subfolders - they're the same as job_output_dir
            
            # Run extraction
            service.run()
            
            # Find generated CSV and JSON files (now in job_output_dir directly)
            csv_files = list(job_output_dir.glob("*.csv"))
            json_files = list(job_output_dir.glob("*.json"))
            
            if csv_files and json_files:
                csv_path = str(csv_files[0])
                json_path = str(json_files[0])
                self.set_job_complete(job_id, csv_path, json_path)
            else:
                self.set_job_error(job_id, "No output files generated")
        
        except Exception as e:
            self.set_job_error(job_id, str(e))
        
        finally:
            # Always clean up the entire upload directory for this job
            try:
                if job_upload_dir and job_upload_dir.exists():
                    shutil.rmtree(job_upload_dir)
                    print(f"Cleaned up temporary files for batch {job_id}")
            except Exception as cleanup_error:
                # Log cleanup error but don't fail the job
                print(f"Warning: Failed to cleanup temporary files for batch {job_id}: {cleanup_error}")  # Ignore cleanup errors on failure
    
    
    def _save_state(self):
        """Save current job state to JSON file (must be called within lock)"""
        try:
            # Note: This method assumes the caller already holds self.lock
            state_data = {
                'jobs': {job_id: job.to_dict() for job_id, job in self.jobs.items()}
            }
            
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def _load_state(self):
        """Load job state from JSON file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                with self.lock:
                    for job_id, job_data in state_data.get('jobs', {}).items():
                        self.jobs[job_id] = Job.from_dict(job_data)
                
                print(f"Loaded {len(self.jobs)} jobs from state file")
            else:
                print("No existing state file found, starting fresh")
        except Exception as e:
            print(f"Error loading state: {e}")
    
    def get_all_jobs(self) -> list:
        """Get all jobs"""
        with self.lock:
            return [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "progress": job.progress,
                    "total_files": job.total_files,
                    "created_at": job.created_at.isoformat(),
                    "message": job.message
                }
                for job in self.jobs.values()
            ]


# Global job manager instance
job_manager = JobManager()
