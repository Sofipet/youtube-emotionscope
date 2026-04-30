# EmotionScope Architecture

## System goal

EmotionScope is an LLM-first analytics system that transforms a YouTube video link into a structured emotional analysis of the comment section.

The system is designed as:

- a compact product-oriented analytics pipeline
- with a stable deterministic core
- and a bounded insight-agent layer on top for grounded follow-up questions

## Final MVP outputs

The MVP has two core product outputs.

### 1. Structured video analysis payload

The core pipeline must produce one structured object with these fields:

- `video`
- `top_primary_emotions`
- `top_nuanced_emotions`
- `valence`
- `timeline`
- `warnings`
- `description`
- `representative_comments`

This object is the single source of truth for:

- API responses
- frontend rendering
- demo payloads
- evaluation
- grounded follow-up answering

### 2. Insight-agent response

The product also includes a bounded follow-up answer layer for the currently analyzed video.

This response contains:

- `answer`
- `suggested_followups`

This layer must stay grounded in the structured analysis payload and must not bypass it.


## High-level flow

The main MVP analysis pipeline runs in this order:

1. user submits a YouTube video URL
2. video metadata and comments are fetched
3. comments are preprocessed and cleaned
4. a smaller comment subset is sampled for analysis
5. sampled comments are classified with an LLM
6. classified comments are aggregated into video-level analytics
7. a short contextual description is generated
8. the final structured payload is returned

Then, optionally:

9. the insight-agent layer answers a grounded follow-up question using the structured payload

The deterministic analysis pipeline is the core analytical engine of the product.  
The insight-agent layer sits on top of that core.


## Architectural layers

### 1. Input and API layer

Responsible for:

- accepting video URLs
- validating requests
- returning structured responses
- supporting demo and live modes
- serving the bounded insight-agent endpoint

Main file:

- `app/api.py`

This layer should stay thin and should not contain analytical logic.


### 2. Provider layer

Responsible for:

- external service access
- API-specific request handling

Main files:

- `app/providers/youtube_provider.py`
- `app/providers/openai_provider.py`

#### YouTube provider responsibilities

- parse video identifiers
- fetch video metadata
- fetch comment threads
- normalize raw API payloads

#### OpenAI provider responsibilities

- classify comments into emotion outputs
- generate the short final description


### 3. Pipeline layer

Responsible for the core deterministic analytics flow.

Main files:

- `app/pipelines/fetch_pipeline.py`
- `app/pipelines/preprocess_pipeline.py`
- `app/pipelines/emotion_pipeline.py`
- `app/pipelines/aggregation_pipeline.py`
- `app/pipelines/description_pipeline.py`

#### Fetch pipeline

Input:

- video URL

Output:

- video metadata
- raw comments
- fetch warnings

Responsibilities:

- coordinate metadata and comment fetching
- detect obvious upstream limitations
- prepare raw input for preprocessing

#### Preprocess pipeline

Input:

- raw comments

Output:

- cleaned comments
- sampled comments
- preprocessing warnings

Responsibilities:

- normalize text
- remove empty and low-value comments
- deduplicate or collapse near-duplicates
- optionally flag unusual content
- produce the final analysis subset

#### Emotion pipeline

Input:

- sampled cleaned comments

Output:

- classified comments
- classification warnings

Responsibilities:

- classify each comment into:
  - `primary_emotion`
  - `nuanced_emotion`
  - `emotion_intensity`
  - `valence`
  - `confidence`
- validate outputs against the schema

#### Aggregation pipeline

Input:

- classified comments

Output:

- `top_primary_emotions`
- `top_nuanced_emotions`
- `valence`
- `timeline`
- `representative_comments`
- aggregation warnings
- language distribution for final video metadata

Responsibilities:

- compute prevalence and average intensity
- build chart-ready structures
- build date-based timeline points
- select representative comments
- attach warnings for sparse or weak analysis conditions
- compute lightweight language metadata for display

#### Description pipeline

Input:

- video-level aggregates
- representative comments
- warnings

Output:

- `description`

Responsibilities:

- generate a short contextual explanation of the emotional picture
- stay grounded in the aggregates and representative comments
- remain concise and warning-aware


### 4. Storage layer

Responsible for:

- caching
- optional local persistence of intermediate and final results
- stable demo artifacts

Main files:

- `app/storage/cache.py`

For the MVP, this should stay lightweight.

Recommended cache layers:

- raw fetch cache
- final analysis cache

Possible uses:

- avoid repeated YouTube API calls
- avoid repeated LLM classification costs
- support stable demo results
- support re-rendering without rerunning expensive stages


### 5. Analysis orchestration layer

Responsible for:

- orchestrating the deterministic core pipeline
- merging warnings
- assembling the final structured response
- handling cache-aware final analysis generation

Main file:

- `app/agents/analysis_agent.py`

#### MVP role

For the MVP, this layer should remain light and mostly deterministic.

Its job is to:

- call the pipeline stages in sequence
- reuse cache when appropriate
- merge warning signals
- assemble the final response object

This layer sits above the pipeline but does not replace it.


### 6. Insight-agent layer

Responsible for:

- answering grounded follow-up questions about the current analyzed video
- selecting internal analytic tools based on question type
- synthesizing concise answers from structured signals

Main files:

- `app/agents/video_insight_agent.py`
- `app/contracts_agent.py`

#### MVP role

For the MVP, this is a bounded, tool-based agent layer.

Its job is to:

- receive the structured analysis payload
- decide which internal tools are relevant
- pull the needed dashboard signals
- generate a concise grounded answer
- suggest useful next questions

It must not:

- browse externally
- act as an open-domain chatbot
- replace the deterministic analysis pipeline

This means the agent layer sits above the structured payload and depends on it.


### 7. Frontend layer

Responsible for:

- video input
- demo/live interaction
- dashboard rendering
- language chip display
- representative comment display
- insight-agent chat-style interaction

Main files:

- `app/web/app.html`
- `app/web/app.js`
- `app/web/styles.css`


## Core data flow

### Input object

- `AnalyzeVideoRequest`

### Main intermediate objects

- raw video metadata
- raw comments
- cleaned comments
- sampled comments
- classified comments
- aggregated analytics
- description prompt inputs

### Final structured analysis object

- `VideoAnalysisResponse`

### Final insight-agent object

- `VideoInsightResponse`

The structured analysis response is the main product contract and must remain stable.  
The insight-agent response is a secondary, grounded interpretation layer built on top of it.


## Why the pipeline is deterministic first

The product includes an agent layer, but it is still built around a deterministic core because that is better for:

- reproducibility
- debugging
- evaluation
- cost control
- portfolio clarity

This is especially important because the main use case includes analytical exploration, where consistency matters.

The insight-agent layer should extend the product, not replace the deterministic pipeline.


## Recommended build order

To keep the project structured, implementation should proceed in this order:

1. contracts
2. settings
3. fetch provider and fetch pipeline
4. preprocess pipeline
5. OpenAI provider
6. emotion pipeline
7. aggregation pipeline
8. description pipeline
9. caching
10. analysis agent
11. API
12. frontend
13. tracing
14. insight-agent layer
15. evaluation


## Expected extension path

Once the MVP is stable, the architecture might support:

- comparing multiple videos
- multilingual analysis modes
- before/after event comparison
- stronger cache and persistence layers
- open-source model benchmarking
- richer tool-based agent behavior on top of the core payload
- richer warning layers such as toxicity or uncertainty signals

