# Curl Samples

These examples show the intended runtime shape of the API.

## Recovery trend

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{"athlete_id":42,"message":"Show my recovery trend over the last 7 days","timezone":"America/Halifax"}'
```

## Readiness comparison

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{"athlete_id":42,"message":"Compare my readiness over the last week compared to last week","timezone":"America/Halifax"}'
```

## Injury-risk trend

```bash
curl -N -X POST "$RHYTHMX_API/chat/" \
  -H "Content-Type: application/json" \
  -d '{"athlete_id":42,"message":"Has my injury risk improved over the last 14 days?"}'
```

The important part is the contract: authenticated athlete, explicit message, optional timezone, and streamed text response.
