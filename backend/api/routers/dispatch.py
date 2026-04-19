"""
Dispatch API — expose job status so the frontend can show
"waiting for employee to be free" banners during team/sprint runs.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from backend.core.dispatch.jobs import load_job

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.get("/jobs/{job_id}")
async def get_dispatch_job(job_id: str):
    job = await load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return asdict(job)
