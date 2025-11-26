from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import json
import os
import asyncio
from typing import Optional

router = APIRouter(prefix="/api/storybook", tags=["storybook"])

# In-memory cache for generated rounds (session -> rounds)
rounds_cache = {}

# Fallback rounds
FALLBACK_ROUNDS = [
    {
        "id": "fallback-4",
        "type": "text",
        "promptText": "Tap the sentences in the correct story order:",
        "items": [
            "A small bird lost its way during a storm.",
            "A kind child found the bird and brought it home.",
            "The bird learned to fly again and thanked the child."
        ],
        "aiGenerated": True
    },
    {
        "id": "fallback-5",
        "type": "text",
        "promptText": "Tap the sentences in the correct story order:",
        "items": [
            "The boy planted a tiny seed in the garden.",
            "A green sprout grew and turned into a plant.",
            "Soon the plant had bright flowers that bees loved."
        ],
        "aiGenerated": True
    }
]

# Pydantic models
class GenerateRoundsRequest(BaseModel):
    preferredLanguage: str = "english"
    sessionId: Optional[str] = None

class GenerateRoundsResponse(BaseModel):
    rounds: list
    source: str  # "ai" or "fallback"

class AnalyzeResponseRequest(BaseModel):
    roundId: str
    promptText: str
    items: list
    userOrder: list
    sessionId: Optional[str] = None
    preferredLanguage: str = "english"

class AnalyzeResponseResponse(BaseModel):
    analysis: dict
    source: str  # "ai" or "fallback"


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from model response."""
    try:
        # Try direct parsing first
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
    return None


def call_gemini_with_retry(prompt: str, max_retries: int = 2) -> Optional[str]:
    """Call Gemini API with retry logic."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        print("ERROR: GEMINI_API_KEY not configured")
        return None
    
    # Configure API key each time (ensures env var is fresh)
    genai.configure(api_key=gemini_api_key)
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            print(f"Gemini API call succeeded on attempt {attempt + 1}")
            return response.text
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # Use time.sleep instead of asyncio.sleep for sync function
    print("ERROR: All Gemini API attempts failed")
    return None


@router.post("/generate-rounds", response_model=GenerateRoundsResponse)
async def generate_rounds(request: GenerateRoundsRequest):
    """Generate 2 AI text rounds for rounds 4 and 5."""
    
    print(f"[generate-rounds] Request received. sessionId={request.sessionId}, language={request.preferredLanguage}")
    
    # Check cache first
    if request.sessionId and request.sessionId in rounds_cache:
        print(f"[generate-rounds] Returning cached rounds for session {request.sessionId}")
        cached = rounds_cache[request.sessionId]
        return GenerateRoundsResponse(rounds=cached, source="ai")
    
    # Build prompt
    prompt = f"""You are a short children's story prompt generator for a dyslexia screening test.
Return exactly 2 rounds as JSON. Each round must have these fields:
- id: string (e.g., "ai-4", "ai-5")
- type: "text"
- promptText: one-line instruction for the child (e.g., "Tap the sentences in the correct story order:")
- items: array of exactly 3 short sentences (each 6–12 words) that form a coherent story

Keep sentences simple, age-appropriate, and in English-friendly structure.
Return ONLY valid JSON with key "rounds" containing an array of 2 round objects.
Language: {request.preferredLanguage}

Example format:
{{"rounds": [{{"id": "ai-4", "type": "text", "promptText": "Tap...", "items": ["...", "...", "..."]}}, {{"id": "ai-5", "type": "text", "promptText": "Tap...", "items": ["...", "...", "..."]}}]}}
"""
    
    # Call Gemini
    print(f"[generate-rounds] Calling Gemini API...")
    response_text = call_gemini_with_retry(prompt)
    
    if not response_text:
        print(f"[generate-rounds] Gemini API returned None, using fallback")
        return GenerateRoundsResponse(rounds=FALLBACK_ROUNDS, source="fallback")
    
    print(f"[generate-rounds] Gemini response received, length={len(response_text)}")
    
    # Parse JSON
    parsed = parse_json_response(response_text)
    if not parsed:
        print(f"[generate-rounds] Failed to parse JSON from response")
        return GenerateRoundsResponse(rounds=FALLBACK_ROUNDS, source="fallback")
    
    if "rounds" not in parsed or len(parsed["rounds"]) < 2:
        print(f"[generate-rounds] Invalid response structure, missing 'rounds' or less than 2 rounds")
        return GenerateRoundsResponse(rounds=FALLBACK_ROUNDS, source="fallback")
    
    # Validate structure
    rounds_data = parsed["rounds"][:2]
    for i, round_data in enumerate(rounds_data):
        if not all(k in round_data for k in ["id", "type", "promptText", "items"]):
            print(f"[generate-rounds] Round {i} missing required fields")
            return GenerateRoundsResponse(rounds=FALLBACK_ROUNDS, source="fallback")
        if len(round_data["items"]) != 3:
            print(f"[generate-rounds] Round {i} has {len(round_data['items'])} items, expected 3")
            return GenerateRoundsResponse(rounds=FALLBACK_ROUNDS, source="fallback")
        round_data["aiGenerated"] = True
    
    # Cache and return
    if request.sessionId:
        rounds_cache[request.sessionId] = rounds_data
        print(f"[generate-rounds] Successfully generated and cached rounds for session {request.sessionId}")
    
    print(f"[generate-rounds] Returning AI-generated rounds")
    return GenerateRoundsResponse(rounds=rounds_data, source="ai")


@router.post("/analyze-response", response_model=AnalyzeResponseResponse)
async def analyze_response(request: AnalyzeResponseRequest):
    """Analyze user response for dyslexia-relevant cues."""
    
    # Build analysis prompt
    user_order_str = ", ".join([str(i) for i in request.userOrder])
    items_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(request.items)])
    
    prompt = f"""You are an expert assessor of reading and sequencing interpretation for dyslexia screening (this is a screening aid, not a diagnosis).

Prompt given to child: "{request.promptText}"

Story sentences:
{items_str}

Child selected and ordered them as: {user_order_str} (using 1-based indices)

Analyze the child's response and return ONLY a JSON object with these fields:
- sequencing: {{score: 0-1, note: "short explanation of sequencing understanding"}}
- omissions: {{score: 0-1, note: "explanation of any missing key elements"}}
- visualConfusion: {{score: 0-1, note: "evidence of visual-letter confusion"}}
- phonologicalCue: {{score: 0-1, note: "evidence of phonological/sound-based reasoning"}}
- recommendedFollowUps: ["question 1", "question 2"]
- confidence: 0-1

Scores: 0=not present, 0.5=possibly present, 1=clearly present.
Return ONLY valid JSON, nothing else.
"""
    
    # Call Gemini
    response_text = call_gemini_with_retry(prompt)
    
    if not response_text:
        # Fallback analysis
        fallback_analysis = {
            "sequencing": {"score": 0.5, "note": "Unable to assess."},
            "omissions": {"score": 0.5, "note": "Unable to assess."},
            "visualConfusion": {"score": 0.1, "note": "No clear visual confusion detected."},
            "phonologicalCue": {"score": 0.2, "note": "No clear phonological emphasis detected."},
            "recommendedFollowUps": ["Ask the child to retell the story.", "Ask why they chose this order."],
            "confidence": 0.3
        }
        return AnalyzeResponseResponse(analysis=fallback_analysis, source="fallback")
    
    # Parse JSON
    parsed = parse_json_response(response_text)
    if not parsed:
        fallback_analysis = {
            "sequencing": {"score": 0.5, "note": "Unable to assess."},
            "omissions": {"score": 0.5, "note": "Unable to assess."},
            "visualConfusion": {"score": 0.1, "note": "No clear visual confusion detected."},
            "phonologicalCue": {"score": 0.2, "note": "No clear phonological emphasis detected."},
            "recommendedFollowUps": ["Ask the child to retell the story.", "Ask why they chose this order."],
            "confidence": 0.3
        }
        return AnalyzeResponseResponse(analysis=fallback_analysis, source="fallback")
    
    # Validate required fields
    required_fields = ["sequencing", "omissions", "visualConfusion", "phonologicalCue", "recommendedFollowUps", "confidence"]
    if not all(field in parsed for field in required_fields):
        fallback_analysis = {
            "sequencing": {"score": 0.5, "note": "Unable to assess."},
            "omissions": {"score": 0.5, "note": "Unable to assess."},
            "visualConfusion": {"score": 0.1, "note": "No clear visual confusion detected."},
            "phonologicalCue": {"score": 0.2, "note": "No clear phonological emphasis detected."},
            "recommendedFollowUps": ["Ask the child to retell the story.", "Ask why they chose this order."],
            "confidence": 0.3
        }
        return AnalyzeResponseResponse(analysis=fallback_analysis, source="fallback")
    
    return AnalyzeResponseResponse(analysis=parsed, source="ai")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    return {"status": "ok", "api_key_configured": bool(gemini_api_key)}
