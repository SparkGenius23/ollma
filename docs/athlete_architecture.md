# Athlete Architecture

RhythmX is organized around athlete-scoped access:

1. JWT authentication identifies the athlete.
2. The client may not choose the database identity.
3. Historical requests are resolved through server-side intent parsing.
4. Trend data is fetched with allowlisted queries only.
5. The model receives a compact analytics payload rather than raw database access.

This keeps the chat experience useful while preserving privacy and control.
