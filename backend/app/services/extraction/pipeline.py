import json
import logging

from app.config import ANTHROPIC_API_KEY
from app.services.extraction.templates import (
    bca_bank,
    bca_sekuritas,
    bni_sekuritas,
    cimb_niaga,
    mandiri_sekuritas,
    stockbit,
)
from app.services.extraction.text_regex import detect_institution, extract_text_from_pdf
from app.services.extraction.vision_llm import extract_with_vision

logger = logging.getLogger(__name__)

# Map institution names to template extractors
_TEMPLATE_EXTRACTORS: dict[str, callable] = {
    "CIMB Niaga": cimb_niaga.extract,
    "BCA Sekuritas": bca_sekuritas.extract,
    "Mandiri Sekuritas": mandiri_sekuritas.extract,
    "BNI Sekuritas": bni_sekuritas.extract,
    "Stockbit": stockbit.extract,
    "BCA": bca_bank.extract,
}


async def extract_document(file_path: str) -> dict:
    """
    Main extraction orchestrator for uploaded PDF documents.

    Pipeline:
    1. Try text extraction with pdfplumber
    2. If text found, detect institution from content
    3. Route to appropriate template extractor
    4. If confidence < 0.8, try vision LLM (if API key available)
    5. Return structured extraction result
    """
    result: dict = {
        "file_path": file_path,
        "institution": None,
        "document_type": None,
        "confidence_score": 0.0,
        "data": {},
        "extraction_method": None,
        "period_start": None,
        "period_end": None,
    }

    # Step 1: Text extraction
    try:
        pages_text = extract_text_from_pdf(file_path)
    except Exception as e:
        logger.error("Failed to extract text from PDF %s: %s", file_path, e)
        pages_text = []

    full_text = "\n".join(pages_text)

    # Step 2: Detect institution
    institution = detect_institution(full_text) if full_text.strip() else None
    result["institution"] = institution

    # Step 3: Route to template extractor
    if institution and institution in _TEMPLATE_EXTRACTORS:
        try:
            extractor = _TEMPLATE_EXTRACTORS[institution]
            template_result = extractor(pages_text)

            if template_result:
                result["data"] = template_result.get("data", {})
                result["confidence_score"] = template_result.get("confidence_score", 0.0)
                result["document_type"] = template_result.get("document_type")
                result["extraction_method"] = "template"
                result["period_start"] = template_result.get("period_start")
                result["period_end"] = template_result.get("period_end")

                logger.info(
                    "Template extraction for %s: confidence=%.2f",
                    institution,
                    result["confidence_score"],
                )
        except Exception as e:
            logger.error("Template extraction failed for %s: %s", institution, e)

    # Step 4: Try vision LLM if confidence is low
    if result["confidence_score"] < 0.8 and ANTHROPIC_API_KEY:
        logger.info("Confidence %.2f < 0.8, attempting vision LLM extraction", result["confidence_score"])
        try:
            vision_result = await extract_with_vision(file_path, institution)
            if vision_result:
                # If template extraction had some results, merge; otherwise replace
                if result["confidence_score"] > 0:
                    result["data"]["vision_supplement"] = vision_result
                    result["confidence_score"] = min(result["confidence_score"] + 0.2, 1.0)
                else:
                    result["data"] = vision_result
                    result["confidence_score"] = 0.85
                    result["extraction_method"] = "vision_llm"

                    # Try to detect institution and document type from vision result
                    if not result["institution"] and isinstance(vision_result, dict):
                        result["institution"] = vision_result.get("institution")
                        result["document_type"] = vision_result.get("document_type")

                logger.info("Vision LLM extraction completed, updated confidence=%.2f", result["confidence_score"])
        except Exception as e:
            logger.error("Vision LLM extraction failed: %s", e)

    # Step 5: If still no extraction, try basic text dump
    if not result["data"] and full_text.strip():
        result["data"] = {"raw_text": full_text[:5000]}
        result["confidence_score"] = 0.1
        result["extraction_method"] = "raw_text"

    return result
