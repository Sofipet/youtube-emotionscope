# EmotionScope Product Contract

## Product goal

Given a YouTube video link, the system analyzes the emotional structure of the comment section and returns a structured analytics payload that can power a dashboard, a short contextual description, and a grounded follow-up insight layer.

The product is designed as a **structured analytics tool with a bounded insight-agent layer**, not as a general chatbot and not as a retrieval system.

---

## Primary user

- researcher
- analyst
- journalist
- student
- product/demo viewer

---

## Input

A single YouTube video URL.

Optional future inputs:
- analysis mode
- language filter
- comment limit
- comparison mode with two or more videos

For the MVP, the required input is:

- `video_url: string`

---

## Core outputs

The MVP has two product outputs:

### 1. Structured video analysis payload
One structured video analysis object with these fields:

- `video`
- `top_primary_emotions`
- `top_nuanced_emotions`
- `valence`
- `timeline`
- `warnings`
- `description`
- `representative_comments`

This output is intended to support both:
- machine-readable frontend rendering
- human-readable analytical interpretation

### 2. Insight-agent response
An optional grounded follow-up answer about the current analyzed video.

The insight-agent response contains:
- `answer`
- `suggested_followups`

This layer must remain grounded in the structured video analysis payload.

---

## Core design principles

- Use a **fixed primary emotion taxonomy** for stable aggregation and visualization.
- Allow limited flexibility through an optional nuanced layer.
- Prefer structured outputs over free-form prose.
- Keep the MVP focused on one-video analysis.
- Separate the analysis pipeline from UI concerns.
- Preserve interpretability through representative comments and warnings.
- Keep the final product payload compact and dashboard-ready.
- Keep the insight-agent layer bounded to the current video analysis payload.

---

## Emotion framework

### Primary emotion taxonomy

Each analyzed comment must receive exactly one `primary_emotion` from this fixed set:

- anger
- fear
- sadness
- disgust
- joy
- trust
- anticipation
- surprise

### Intensity

Each analyzed comment must also receive:

- `emotion_intensity: float`

Range:
- minimum: `0.0`
- maximum: `1.0`

Interpretation:
- `0.0` = no meaningful emotional intensity
- `1.0` = maximally strong emotional intensity

### Valence

Each analyzed comment must receive:

- `valence: one of ["positive", "negative", "mixed", "neutral"]`

### Nuanced emotion

Each analyzed comment may optionally receive:

- `nuanced_emotion: string | null`

This field is used only when the model identifies a short, meaningful affective nuance not fully captured by the fixed taxonomy.

Examples:
- moral outrage
- helplessness
- solidarity
- anxiety
- sarcasm

This field must remain short and interpretable.

### Confidence

Each analyzed comment must receive:

- `confidence: float`

Range:
- minimum: `0.0`
- maximum: `1.0`

Interpretation:
- confidence in the assigned primary emotion / valence judgment

---

## Comment-level schema

Each classified comment must contain:

- `comment_id: string`
- `published_at: string`
- `like_count: int`
- `text_original: string`
- `text_clean: string`
- `detected_language: string | null`
- `primary_emotion: enum`
- `emotion_intensity: float`
- `valence: enum`
- `nuanced_emotion: string | null`
- `confidence: float`

Optional future fields:
- reply count
- author id
- translation
- toxicity / stance / irony flags

---

## Final video-level output schema

### 1. `video`
Basic metadata and analysis volume information:

- `video_id: string`
- `video_url: string`
- `title: string`
- `channel_title: string | null`
- `published_at: string | null`
- `comments_fetched: int`
- `comments_analyzed: int`
- `languages: list`

Each language item contains:
- `language_code: string`
- `language_label: string`
- `share: float`

### 2. `top_primary_emotions`
Main emotional profile of the analyzed comments.

Each item contains:
- `emotion`
- `prevalence`
- `avg_intensity`

Only the most relevant primary emotions should be returned in the final payload.

### 3. `top_nuanced_emotions`
Secondary interpretive emotional layer derived from repeated nuanced labels.

Each item contains:
- `emotion`
- `prevalence`
- `avg_intensity`

Only repeated and meaningful nuanced emotions should be returned.

### 4. `valence`
Overall valence distribution:

- `positive`
- `negative`
- `mixed`
- `neutral`

### 5. `timeline`
Date-based emotional change over comment time.

Each timeline point contains:
- `date`
- `comment_count`
- `primary_emotions`
- `valence`

Where:
- `primary_emotions` uses the same structure as `top_primary_emotions`
- `valence` uses the same structure as the top-level valence object

### 6. `warnings`
Simple warning labels describing important limitations.

Examples:
- too_few_comments
- multilingual_mix
- low_confidence_distribution
- sparse_timeline
- api_partial_data

### 7. `description`
A short 1–2 sentence contextual explanation of the emotional picture.

The description should:
- stay grounded in the aggregates and representative comments
- briefly explain why the dominant emotions may appear
- acknowledge limitations when warnings are present

### 8. `representative_comments`
A small set of comments that best illustrate major emotional patterns.

Each item contains:
- `comment_id`
- `primary_emotion`
- `nuanced_emotion`
- `emotion_intensity`
- `valence`
- `like_count`
- `text`

---

## Insight-agent response schema

The bounded insight-agent layer answers grounded follow-up questions about the current analyzed video.

Each response contains:

- `answer: string`
- `suggested_followups: list[string]`

### Insight-agent expectations

The insight-agent should:
- answer only on the basis of the structured analysis payload
- remain concise and product-appropriate
- avoid unsupported claims
- avoid acting like a general chatbot
- support follow-up exploration of the current video

The insight-agent should not:
- invent evidence not present in the current payload
- behave like a retrieval system
- browse the web
- answer unrelated general questions

---

## Dashboard payload expectations

The frontend should be able to render at least:

- top primary emotions
- top nuanced emotions
- valence distribution
- timeline
- representative comments
- description card
- warning banner
- language chips
- insight-agent panel

The API output must therefore be complete enough that the frontend does not need to derive major analytical logic itself.

---

## Non-goals for MVP

- no cross-video comparison in the main product flow
- no real-time streaming analysis
- no retrieval layer
- no ticketing / CRM integration
- no arbitrary open-ended emotion taxonomies
- no unlimited public live inference
- no autonomous posting or moderation actions
- no open-domain conversational assistant behavior

---

## Initial deployment shape

- FastAPI backend
- custom HTML/CSS/JS frontend
- demo mode
- protected live mode
- OpenAI-based baseline
- cached or stored analysis results where useful
- bounded insight-agent layer over the current video payload

---

## Future extensions

Possible future extensions include:
- multi-video comparison
- before/after event comparison
- multilingual comparison
- exportable reports
- stronger open-source model benchmarking
- richer agent planning over analysis modes
- toxicity / toxicity-warning layer
- broader analyst workflows over multiple saved videos