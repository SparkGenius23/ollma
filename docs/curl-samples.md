# Intelligence Engine curl samples

The following samples send the AI context payloads used by the readiness,
injury-risk, recovery, and overall-state flows. Replace `$OPENAI_INTEL` with
the configured AI service base URL.

## Historical trend and comparison chat

Replace `$RHYTHMX_API` with the FastAPI base URL. The `/chat/` endpoint reads
the numeric Django `auth.User` primary key from `athlete_id`. `timezone` is
optional and defaults to `UTC` when omitted.

### Recovery trend - last 7 days

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 42,
    "message": "Show my recovery trend over the last 7 days",
    "timezone": "America/Halifax"
  }'
```

### Readiness comparison - current week versus prior week

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 42,
    "message": "Compare my readiness over the last week compared to last week",
    "timezone": "America/Halifax"
  }'
```

### Recovery versus readiness - last 30 days

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 42,
    "message": "Compare my recovery versus readiness over the last 30 days"
  }'
```

### Injury-risk trend - last 14 days

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 42,
    "message": "Has my injury risk improved over the last 14 days?"
  }'
```

`-N` keeps curl from buffering the streamed text response. The chat service
returns `503` when the database is not configured or unavailable, and `422`
when the request body, athlete ID, timezone, or message is invalid.

## Readiness

```bash
curl -X POST "$OPENAI_INTEL/readiness" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "\\nUSER_CONTEXT:\\n\\nuser_segment: ATHLETE\\nuser_role: ATHLETE\\nsport_type: Soccer\\nsex: Male\\nillness_flag: False\\ndays_since_return: NA\\nweight: 78.5\\nheight: 180cm\\n\\n=== READINESS (caution) ===\\nReadiness Score: 74\\nHeat Stress (context) — NA\\n3. HRV (RMSSD) (physiological) — 52.8%\\nReadiness Zone: Moderate\\nPenalty Factor: [\\\"mild_knee_pain\\\"]\\nrecommended_actions: Reduce high-intensity volume today Focus on hydration and mobility\\nConfidence gating: {\\\"level\\\": \\\"high\\\", \\\"reason\\\": \\\"sufficient_hrv_and_wellness_data\\\"}\\nPhysio Score: 81.0%\\nCardiac Component: 76.0\\n"
  }'
```

## Injury risk

```bash
curl -X POST "$OPENAI_INTEL/risk" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "\\n=== INJURY RISK (normal) ===\\nHRV (RMSSD) (physiological) — 52.8%\\nHeat Stress (context) — NA\\nInjury Risk Score: 37\\nRisk Band: Moderate\\nRisk zone: Yellow\\nStartup phase flag: False\\nRisk Factors: [\\\"Acute workload increase\\\", \\\"Mild knee pain\\\", \\\"Below-baseline HRV\\\"]\\nrecommended_actions: Reduce high-intensity training by 20% Prioritize mobility and recovery Monitor knee discomfort\\nConfidence gating: {\\\"level\\\": \\\"high\\\", \\\"reason\\\": \\\"sufficient wellness, workload, and HRV history\\\"}\\n"
  }'
```

## Recovery

```bash
curl -X POST "$OPENAI_INTEL/recovery" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "\\n=== RECOVERY (normal) ===\\nHRV (RMSSD) (physiological) — 52.8% — HRV score: 82\\nFatigue score (Subjective) (perceptual) — 68\\nHeat Stress (context) — NA\\nRecovery Score: 76\\nSleep Score: 80\\nRHR Score: 78\\nProtein Ratio: 72\\nHydration Score: 84\\nARI Score: 75\\nSPO2 Score: 98\\nStress Score: 70\\nSoreness Score: 74\\nPenalty Factor: mild_fatigue\\nInterpretation Band: Good\\nrecommended_actions: Maintain moderate training volume Prioritize hydration and consume adequate protein Continue regular sleep schedule\\nConfidence gating: {\\\"level\\\": \\\"high\\\", \\\"reason\\\": \\\"sufficient HRV, wellness, and recovery history\\\"}\\n"
  }'
```

## Overall state / health band

```bash
curl -X POST "$OPENAI_INTEL/health-band" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "\\n=== OVERALL STATE ===\\nRecovery Score: 76\\nReadiness Score: 74\\nInjury Risk Score: 37\\nHealth band score: 78\\nBand Confidence: 0.92\\nmodel_confidence: high\\nStart up flag: False\\nHRV score: 82\\nFatigue score (Subjective) (perceptual) — 68\\nHeat Stress (context) — NA\\nSleep Score: 80\\nRHR Score: 78\\nProtein Ratio: 72\\nHydration Score: 84\\nARI Score: 75\\nSPO2 Score: 98\\nStress Score: 70\\nSoreness Score: 74\\nRecovery Interpretation Band: Good\\nrecommended_actions: Maintain moderate training volume Prioritize hydration and protein intake Monitor knee discomfort and avoid high-impact work today\\nConfidence gating: {\\\"level\\\": \\\"high\\\", \\\"reason\\\": \\\"sufficient recovery, readiness, injury-risk, HRV, and wellness data\\\"}\\nDominant concern: Moderate injury risk due to acute workload increase and mild knee pain.\\n"
  }'
```
