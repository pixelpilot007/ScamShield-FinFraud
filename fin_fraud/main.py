from fastapi import FastAPI, UploadFile, File, HTTPException
from fin_fraud.config import settings
from fin_fraud.llm import extract_text_from_image, analyze_risk_evidence, transcribe_audio
from fin_fraud.logic import analyze_image_risk
from PIL import Image
import io
import uuid
from typing import List
from loguru import logger
from qdrant_client.http import models

app = FastAPI(title="ScamShield FinFraud", version="0.1.0")

HISTORY_COLLECTION = "user_history"

@app.on_event("startup")
async def startup_event():
    """
    Ensure the user_history collection exists for long-term memory.
    """
    client = settings.get_qdrant_client()
    try:
        collections = client.get_collections().collections
        exists = any(c.name == HISTORY_COLLECTION for c in collections)

        if not exists:
            logger.info(f"Creating {HISTORY_COLLECTION} collection for Long-term Memory...")
            client.create_collection(
                collection_name=HISTORY_COLLECTION,
                vectors_config=models.VectorParams(
                    size=768, # Matching BGE-base standard (768 dims)
                    distance=models.Distance.COSINE
                )
            )
    except Exception as e:
        logger.error(f"Could not initialize {HISTORY_COLLECTION}: {e}")

@app.get("/")
async def root():
    return {"message": "ScamShield FinFraud is running", "mode": "Cloud" if settings.USE_CLOUD else "Local"}

@app.post("/analyze_risk/")
async def analyze_risk(files: List[UploadFile] = File(...)):
    aggregated_text = ""
    visual_evidence = []
    memory_context = ""

    try:
        inputs_processed = 0

        for file in files:
            content = await file.read()
            filename = file.filename

            # --- IMAGE PROCESSING ---
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    pil_image = Image.open(io.BytesIO(content))
                    visual_result = analyze_image_risk(pil_image)
                    if visual_result["risk_level"] in ["High", "Medium", "Low"]:
                        visual_evidence.append({"filename": filename, "visual_risk": visual_result})
                except Exception as v_err:
                    logger.error(f"Visual fail: {v_err}")

                extracted = extract_text_from_image(content)
                if extracted:
                    aggregated_text += f"\n--- Source: {filename} (Image Text) ---\n{extracted}\n"
                    inputs_processed += 1

            # --- AUDIO PROCESSING ---
            elif filename.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg')):
                mime = "audio/mp3"
                if filename.lower().endswith('.wav'): mime = "audio/wav"
                elif filename.lower().endswith('.m4a'): mime = "audio/mp4"

                transcript = transcribe_audio(content, mime_type=mime)
                if transcript:
                    aggregated_text += f"\n--- Source: {filename} (Audio Transcript) ---\n{transcript}\n"
                    inputs_processed += 1

            # --- TEXT FILE PROCESSING ---
            elif filename.endswith('.txt'):
                text = content.decode('utf-8', errors='replace')
                if text.strip():
                    aggregated_text += f"\n--- Source: {filename} (Chat Log) ---\n{text.strip()}\n"
                    inputs_processed += 1

        # --- PHASE 2: SEARCH GENOME (Public Database) ---
        # Disabled on free hosting to reduce memory usage.
        similar_text_cases = []
        memory_context = ""
        query_vector = None

        logger.warning(
            "Embedding search and user history disabled on free hosting."
        )

        # --- PHASE 3: FINAL REASONING (LLM) ---
        visual_summary = ""
        for item in visual_evidence:
            v = item['visual_risk']
            visual_summary += f"- Image '{item['filename']}' detected as {v['risk_level']} Risk. Analysis: {v['analysis']}\n"

        final_user_content = f"""
        {memory_context if memory_context else ""}

        VISUAL EVIDENCE FOUND:
        {visual_summary if visual_summary else "No specific visual scam patterns detected."}

        TEXTUAL/AUDIO EVIDENCE:
        {aggregated_text if aggregated_text else "No readable text found."}
        """

        llm_analysis = analyze_risk_evidence(final_user_content, similar_text_cases)

        # --- PHASE 4: PERSIST TO MEMORY ---
        # Disabled on free hosting because embeddings are unavailable.
        logger.info("Long-term memory persistence skipped.")

        return {
            "inputs_processed": inputs_processed,
            "final_verdict": llm_analysis,
            "detailed_evidence": {
                "visual_analysis": visual_evidence,
                "text_matches": similar_text_cases,
                "aggregated_text": aggregated_text,
                "memory_context": memory_context
            }
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
