"""
StreetSense -- Inference API Endpoint

Run AI detection without creating complaints.
Useful for testing, preview, and live feed processing.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from app.schemas.complaint import InferenceResponse
from app.services import ai_service
from app.utils.file_utils import read_image_from_upload, validate_image_file

router = APIRouter(prefix="/inference", tags=["inference"])


@router.post("/detect", response_model=InferenceResponse)
async def detect_only(file: UploadFile = File(...)):
    """
    Run AI detection on an image WITHOUT creating complaints.
    Returns detection results, annotated image, and depth map.
    """
    error = validate_image_file(file)
    if error:
        raise HTTPException(status_code=400, detail=error)

    content = await file.read()
    try:
        image = read_image_from_upload(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await ai_service.run_inference(image)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="AI inference failed")

    return InferenceResponse(
        image_id=result["image_id"],
        detections=[
            {
                "issue_type": d["issue_type"],
                "confidence": d["confidence"],
                "bbox": d["bbox"],
                "depth_value": d.get("depth_value"),
                "severity": d["severity"],
                "severity_score": d["severity_score"],
            }
            for d in result["detections"]
        ],
        annotated_image_url=result.get("annotated_image_url"),
        depth_map_url=result.get("depth_map_url"),
        processing_time_ms=result["processing_time_ms"],
    )


@router.get("/status")
async def inference_status():
    """Check if AI models are loaded and ready."""
    loaded = ai_service.is_pipeline_loaded()
    return {
        "ai_ready": loaded,
        "models": {
            "yolo": loaded,
            "midas": loaded,
        },
    }
