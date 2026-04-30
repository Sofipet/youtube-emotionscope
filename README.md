# YouTube EmotionScope

An LLM-first analytics app for exploring the emotional structure of YouTube comment sections.

- **Live demo:** [Render App](https://youtube-emotionscope.onrender.com/)

## Interface preview

- **Dashboard overview:**
<img width="1258" height="474" alt="EmotionScope dashboard overview" src="https://github.com/user-attachments/assets/5ed4c4b5-88d1-4e8a-9bce-f6dab87b65e9" />


- **Insight layer:**
<img width="1251" height="573" alt="EmotionScope insight layer" src="https://github.com/user-attachments/assets/d0229efa-4b4c-482c-a9d8-2c8cbda1857b" />

## Overview

EmotionScope transforms a single YouTube video link into a structured emotional analysis of its comment section.

The system is designed as a **bounded analytics product**, not a general chatbot. It combines a deterministic analysis pipeline with a lightweight insight layer to help users move from raw comments to interpretable emotional patterns, representative comments, language mix, timeline shifts, and short contextual summaries.

## What the system does

Given a YouTube video link, EmotionScope:

- fetches video metadata and comments
- preprocesses and samples comments for analysis
- classifies comments into a fixed primary emotion taxonomy
- assigns valence, intensity, and optional nuanced emotion labels
- aggregates comment-level outputs into video-level emotional signals
- generates a short contextual description
- supports a bounded insight layer for follow-up analytical questions

## Example use case

A user pastes a news video about a missile attack on a children’s hospital.

EmotionScope returns:

- dominant primary emotions
- overall valence distribution
- language mix
- representative comments
- a simple emotional timeline
- a short explanation of the emotional picture

The user can then ask a follow-up question such as:

> Is the emotional tone closer to moral outrage or collective grief?

## Architecture

### Core analytics pipeline
- YouTube fetch layer
- preprocessing and sampling
- batch emotion classification
- deterministic aggregation
- description generation

### Insight layer
- bounded agent-style analytical answering
- tool-based access to structured dashboard signals
- lightweight LangChain orchestration
- designed for interpretability, not unrestricted reasoning

### App layer
- FastAPI backend
- custom HTML / CSS / JavaScript frontend
- demo mode + protected live mode
- Dockerized deployment

## Emotion framework

### Primary emotion taxonomy
Each analyzed comment receives one primary emotion from:

- anger
- fear
- sadness
- disgust
- joy
- trust
- anticipation
- surprise

### Additional fields
Each comment may also include:

- valence (`positive`, `negative`, `mixed`, `neutral`)
- emotion intensity
- optional nuanced emotion
- confidence

## Output structure

The main video-level output contains:

- `video`
- `top_primary_emotions`
- `top_nuanced_emotions`
- `valence`
- `timeline`
- `warnings`
- `description`
- `representative_comments`

This output is designed to support both:
- machine-readable frontend rendering
- human-readable interpretation

## Model setup

### Classification and description
- Primary baseline: `gpt-4o-mini`

### Insight layer
- Baseline: `gpt-4o-mini`

## Tech stack

- Python
- FastAPI
- OpenAI API
- Pydantic
- LangChain
- HTML / CSS / JavaScript
- Docker
- LangSmith

## Evaluation

EmotionScope was evaluated as an **analytics product**, not only as a text-generation system.

### Evaluation setup

| Component | Scope |
|---|---:|
| Videos | 3 |
| Comment-level eval cases | 30 |
| Agent cases | 4 |

All structural checks and expected-vs-generated comparison checks passed on the selected MVP evaluation set.

### Manual review averages

| Metric | Score |
|---|---:|
| Description groundedness | 0.833 |
| Description clarity | 1.000 |
| Description usefulness | 1.000 |
| Description consistency | 0.833 |
| Description non-overclaiming | 0.833 |
| Agent groundedness | 0.875 |
| Agent usefulness | 0.875 |
| Agent conciseness | 0.875 |
| Agent non-redundancy | 0.750 |
| Agent consistency | 0.875 |

### Key takeaway

- The MVP performed strongly on structured validity and expected-vs-generated consistency.
- The dashboard outputs are well grounded in representative comments and broad discourse patterns.
- The main remaining weakness is **presentation quality**, not core analytical correctness:
  - one description is weaker than the others
  - some agent answers still sound formulaic
  - follow-up suggestions are too generic

## User experience

The app supports two modes:

### Demo mode
Returns stored example outputs without live API cost.

### Live mode
Supports live video analysis and bounded insight questions with lightweight protection and request limits.

The interface shows:

- video metadata
- language mix
- top emotions
- valence
- timeline
- representative comments
- short description
- optional insight answers in a chat-style section

## Run locally

```bash
git clone https://github.com/YOUR_USERNAME/youtube-emotionscope.git
cd youtube-emotionscope
pip install -r requirements.txt

export OPENAI_API_KEY="your_openai_api_key"
export YOUTUBE_API_KEY="your_youtube_api_key"
export APP_ENV="development"
export APP_ACCESS_TOKEN="your_access_token"
export LIVE_REQUEST_LIMIT="3"

uvicorn app.api:app --reload
```
Open http://127.0.0.1:8000

## Limitations

- an MVP / showcase deployment, not a large-scale production platform
- the evaluation set is relatively small and optimistic
- comment sampling still trades off coverage and cost
- the insight layer is intentionally narrow and does not support unrestricted analytical interaction
- some descriptions and follow-up suggestions still need style refinement
- cache behavior in deployment is suitable for MVP usage, not long-term durable storage

## Future improvements

- improve description style consistency
- make insight answers more specific and less formulaic
- improve follow-up suggestion quality
- expand the evaluation set with harder and more diverse cases
- compare stronger open-source baselines under the same setup
- extend the bounded insight layer while preserving interpretability
