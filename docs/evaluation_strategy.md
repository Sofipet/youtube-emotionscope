# EmotionScope Evaluation Strategy

## Goal

Evaluate EmotionScope as a structured emotional analytics product.

The system should be evaluated as:

- a comment-level emotion classification pipeline
- a video-level aggregation and dashboard system
- a short-description generator
- a bounded insight-agent layer for grounded follow-up questions

The goal is not to treat EmotionScope as a ground-truth detector of human emotion.  
The goal is to assess whether it is:

- plausible
- internally consistent
- grounded
- useful
- operationally practical


## Evaluation scope

This MVP evaluation uses:

- **3 videos**
- **30 manually reviewed comments**
- **4 agent questions**

This is a small but structured evaluation set intended for MVP validation, not large-scale benchmarking.


## Evaluation layers

### 1. Structured output

**Purpose:** verify that outputs are machine-usable and contract-valid.

This layer checks whether the system consistently returns valid structured outputs.

#### Checks

For comment-level outputs:
- schema valid = 100%
- required fields present = 100%
- valid `primary_emotion` label = 100%
- valid `valence` label = 100%
- `emotion_intensity` in `[0,1]` = 100%
- `confidence` in `[0,1]` = 100%

For video-level outputs:
- schema valid = 100%
- required fields present = 100%
- prevalence values in `[0,1]` = 100%
- average intensity values in `[0,1]` = 100%
- valence values in `[0,1]` = 100%
- timeline points structurally valid = 100%
- language shares in `[0,1]` = 100%

For agent outputs:
- schema valid = 100%
- `answer` present = 100%
- `suggested_followups` valid list = 100%

#### Thresholds

- schema_valid = 100%
- required_fields_present = 100%
- numeric_range_validity = 100%


### 2. Comment-level classification

**Purpose:** verify that individual comment classifications are plausible.

#### Evaluation unit

- 30 manually reviewed comments

#### Review fields

- `primary_emotion`
- `valence`
- `emotion_intensity`
- `nuanced_emotion`

#### Manual metrics

- `average_primary_emotion_score`
- `average_valence_score`
- `average_intensity_score`
- `average_nuanced_usefulness_score`

#### Manual review scale

- `1.0` = strong / clearly plausible
- `0.5` = partly plausible / borderline
- `0.0` = weak / clearly implausible

#### Thresholds

- average_primary_emotion_score >= 0.75
- average_valence_score >= 0.80
- average_intensity_score >= 0.70
- average_nuanced_usefulness_score >= 0.60


### 3. Video-level aggregation

**Purpose:** verify that comment-level outputs are aggregated into meaningful dashboard signals.

#### Evaluation unit

- 3 video cases

#### Review fields

- dominant emotion plausibility
- secondary emotion plausibility
- valence plausibility
- representative comment match quality
- timeline usefulness
- warning appropriateness
- language mix plausibility

#### Metrics

- `dominant_emotion_match_rate`
- `average_top_primary_plausibility`
- `average_top_nuanced_usefulness`
- `average_representative_comment_match`
- `average_timeline_usefulness`
- `average_warning_appropriateness`
- `average_language_plausibility`

#### Manual review scale

- `1.0` = strong
- `0.5` = partly useful / partly plausible
- `0.0` = weak / misleading

#### Thresholds

- dominant_emotion_match_rate >= 0.67
- average_top_primary_plausibility >= 0.75
- average_representative_comment_match >= 0.80
- average_timeline_usefulness >= 0.60
- average_warning_appropriateness >= 0.70
- average_language_plausibility >= 0.70


### 4. Description quality

**Purpose:** verify that the generated description is grounded, concise, and useful.

#### Evaluation unit

- 3 video descriptions

#### Review fields

- groundedness
- clarity
- usefulness
- consistency with dashboard
- non-overclaiming

#### Metrics

- `average_description_groundedness`
- `average_description_clarity`
- `average_description_usefulness`
- `average_description_consistency`
- `average_description_non_overclaiming`

#### Manual review scale

- `1.0` = strong
- `0.5` = partly useful / somewhat generic
- `0.0` = weak / misleading

#### Thresholds

- average_description_groundedness >= 0.80
- average_description_clarity >= 0.75
- average_description_usefulness >= 0.70
- average_description_consistency >= 0.80
- average_description_non_overclaiming >= 0.85


### 5. Insight-agent behavior

**Purpose:** verify that the bounded agent answers questions in a grounded and useful way.

#### Evaluation unit

- 4 agent question cases

#### Review fields

- answer groundedness
- answer usefulness
- answer conciseness
- answer non-redundancy
- answer consistency with dashboard
- tool-use sanity

#### Metrics

- `average_agent_groundedness`
- `average_agent_usefulness`
- `average_agent_conciseness`
- `average_agent_nonredundancy`
- `average_agent_consistency`
- `average_tool_use_sanity`

#### Manual review scale

- `1.0` = strong
- `0.5` = partly useful / somewhat generic
- `0.0` = weak / unsupported

#### Thresholds

- average_agent_groundedness >= 0.80
- average_agent_usefulness >= 0.75
- average_agent_conciseness >= 0.75
- average_agent_nonredundancy >= 0.70
- average_agent_consistency >= 0.80
- average_tool_use_sanity >= 0.75


### 6. Runtime, cache, and cost behavior

**Purpose:** verify that the product is practical to run.

#### Review fields

For video runs:
- total latency
- comments fetched
- comments analyzed
- analysis cache hit / miss
- approximate cost

For agent runs:
- answer latency
- agent cache hit / miss
- approximate cost

#### Metrics

- `average_analysis_latency_seconds`
- `average_agent_latency_seconds`
- `average_analysis_cost`
- `average_agent_cost`
- `analysis_cache_hit_rate`
- `agent_cache_hit_rate`

#### Practical thresholds

For main analysis:
- average_analysis_latency_seconds <= 90 for MVP acceptability

For agent layer:
- average_agent_latency_seconds <= 2 preferred
- average_agent_latency_seconds <= 4 acceptable

No strict cost threshold is required for MVP, but cost should remain stable and interpretable.


## Release gates

Reject a candidate version if any of the following occur:

- schema_valid < 100%
- required fields missing
- invalid labels or out-of-range numeric fields appear
- representative comments are not real comments from the analyzed payload
- average_description_groundedness is below threshold
- average_agent_groundedness is below threshold
- repeated unsupported claims appear in descriptions or agent answers
- dominant emotion plausibility is clearly weak
- cache behavior is broken or inconsistent
- latency becomes unacceptable relative to quality gains


## Change policy

Before any major change, record:

- structured output checks
- comment-level metrics
- video-level metrics
- description metrics
- agent metrics
- runtime / cache / cost behavior

After the change, rerun the same evaluation set and compare.

### Major changes include

- classification prompt changes
- description prompt changes
- agent prompt changes
- preprocessing changes
- sampling changes
- aggregation logic changes
- timeline logic changes
- warning logic changes
- model changes
- schema changes
- cache behavior changes
- agent tool selection behavior changes

### Accept a change only if

- quality improves, or
- quality remains acceptable while another tradeoff improves
  - such as latency
  - cost
  - maintainability
  - stability


## Optional tracking

When useful, also track:

- fetch latency
- preprocessing latency
- classification latency
- aggregation latency
- description latency
- model name
- approximate tokens
- approximate cost by stage
- prompt version
- agent version tag


## Manual review policy

Manual review is required for:

- new classification prompts
- new description prompts
- new agent prompts
- new models
- major aggregation changes
- warning logic changes
- release candidates

This is necessary because many key qualities in EmotionScope are interpretive and cannot be fully captured by automatic checks alone.


# Practical interpretation rule

EmotionScope should not be treated as a ground-truth detector of human emotion.

It should be treated as:

- a structured interpretive analytics tool
- a system for surfacing likely emotional patterns
- a dashboard for exploration
- an analyst-support product

Therefore, evaluation should prioritize:

- plausibility
- consistency
- groundedness
- usefulness
- transparency

rather than artificial certainty.
