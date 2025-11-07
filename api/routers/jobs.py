from fastapi import APIRouter, Request, HTTPException
from api.schemas import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, request: Request):
    app = request.app
    job = app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    # incluir campos opcionais conforme disponíveis
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status"),
        progress=job.get("progress"),
        eta_seconds=None,
        duration_seconds=job.get("duration_seconds"),
        result=job.get("result"),
        error=job.get("error"),
    )