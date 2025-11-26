# LexiAssist Backend

Backend API for the LexiAssist dyslexia screening app. Provides endpoints for generating AI-powered story rounds and analyzing user responses using Google's Gemini API.

## Setup

### 1. Get Gemini API Key

1. Go to [ai.google.dev](https://ai.google.dev)
2. Sign in with your Google account
3. Create a new API key (free tier available)
4. Copy the API key

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_api_key_here
```

### 4. Run the Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

The server will start at `http://localhost:8000`

## API Endpoints

### Generate Rounds
**POST** `/api/storybook/generate-rounds`

Generate 2 AI-created text rounds for the storybook challenge. Each round contains 5-6 sentences strategically designed to test for dyslexia markers (visual confusion, phonological cues, sequencing).

**Request:**
```json
{
  "preferredLanguage": "english",
  "sessionId": "optional-session-id"
}
```

**Response (Success):**
```json
{
  "rounds": [
    {
      "id": "ai-4",
      "type": "text",
      "promptText": "Tap the sentences in the correct story order:",
      "items": ["Sentence 1", "Sentence 2", "Sentence 3", "Sentence 4", "Sentence 5", "Sentence 6"],
      "aiGenerated": true
    },
    {
      "id": "ai-5",
      "type": "text",
      "promptText": "Tap the sentences in the correct story order:",
      "items": ["Sentence 1", "Sentence 2", "Sentence 3", "Sentence 4", "Sentence 5"],
      "aiGenerated": true
    }
  ],
  "source": "ai"
}
```

**Sentence Design:**
- 5-6 sentences per round (increased from 3 for more diagnostic depth)
- Includes visually confusing letter pairs: b/d, p/q, n/u
- Includes phonologically similar words (different meanings)
- Includes temporal sequencing words: first, then, after, before, finally
- Varied sentence length and structure
- Coherent narrative for proper sequencing assessment

**Response (Fallback):**
```json
{
  "rounds": [...],
  "source": "fallback"
}
```

### Analyze Response
**POST** `/api/storybook/analyze-response`

Analyze user's ordering for dyslexia-relevant cues. The analysis focuses on detecting patterns that the intentionally-challenging sentences were designed to expose.

**Request:**
```json
{
  "roundId": "ai-4",
  "promptText": "Tap the sentences in the correct story order:",
  "items": ["Sentence 1", "Sentence 2", "Sentence 3", "Sentence 4", "Sentence 5"],
  "userOrder": [2, 1, 3, 4, 5],
  "sessionId": "optional-session-id",
  "preferredLanguage": "english"
}
```

**Response:**
```json
{
  "analysis": {
    "sequencing": {
      "score": 0.6,
      "note": "Child partially understood temporal sequence but struggled with connector words."
    },
    "omissions": {
      "score": 0.1,
      "note": "No key elements omitted from the sequence."
    },
    "visualConfusion": {
      "score": 0.8,
      "note": "Evidence of b/d confusion: child mixed sentences with 'bed' and 'doll' suggesting letter-shape difficulty."
    },
    "phonologicalCue": {
      "score": 0.7,
      "note": "Child prioritized sound patterns over visual word forms in ordering decisions."
    },
    "recommendedFollowUps": [
      "Ask the child to read the sentences aloud and listen for similar sounds.",
      "Point out letter pairs (b/d, p/q) and ask the child to distinguish them.",
      "Have the child retell the story in their own words to assess comprehension."
    ],
    "confidence": 0.85
  },
  "source": "ai"
}
```

**Analysis Markers:**
- **visualConfusion**: 0-1 scale detecting evidence of b/d, p/q, n/u letter-shape confusion
- **phonologicalCue**: 0-1 scale detecting if child relies on sound patterns over visual form
- **sequencing**: 0-1 scale measuring ability to order by temporal cues (first, then, after, before, finally)
- **omissions**: 0-1 scale for missing narrative elements
- **recommendedFollowUps**: Targeted assessment questions based on detected patterns

### Health Check
**GET** `/health`

Check API health and configuration status.

## Development

### Project Structure
```
backend/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment config
├── .gitignore             # Git ignore file
└── routes/
    ├── __init__.py
    └── storybook.py       # Storybook endpoints
```

### Running in Development
```bash
uvicorn backend.main:app --reload --port 8000
```

Auto-reloading enabled for development.

### API Documentation
Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Notes

- **Free Tier Limits:** ~60 requests/minute, ~1500 requests/day
- **Timeout:** 12 seconds per API call
- **Caching:** Generated rounds are cached per `sessionId` to avoid repeated calls
- **Fallback:** Hardcoded fallback rounds are returned if generation fails (2 rounds with 3 sentences each)
- **CORS:** Enabled for all origins (configure for production)
- **AI Sentence Generation:** Each round now generates 5-6 sentences (increased from 3) with:
  - Visual confusion markers (b/d, p/q, n/u letter pairs)
  - Phonological confusion markers (similar sounds, different meanings)
  - Temporal sequencing words (first, then, after, before, finally)
- **Response Analysis:** Enhanced Gemini prompt specifically looks for evidence of visual/phonological confusion patterns in user ordering choices

## Frontend Integration

The frontend should call these endpoints:

```javascript
// Generate rounds
fetch('http://localhost:8000/api/storybook/generate-rounds', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ preferredLanguage: 'english', sessionId: 'user-123' })
});

// Analyze response
fetch('http://localhost:8000/api/storybook/analyze-response', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    roundId: 'ai-4',
    promptText: '...',
    items: [...],
    userOrder: [...]
  })
});
```

## Troubleshooting

**API key not found:**
- Ensure `.env` file exists in the `backend` directory
- Verify `GEMINI_API_KEY` is set correctly
- Check `/health` endpoint

**CORS errors:**
- Ensure `CORSMiddleware` is configured in `main.py`
- In development, it's set to allow all origins

**Timeout errors:**
- Check internet connection
- Verify Gemini API is accessible
- Check rate limits (free tier: 60 req/min)

## License

MIT
