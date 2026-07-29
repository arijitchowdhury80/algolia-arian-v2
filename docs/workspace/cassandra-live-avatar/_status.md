# Cassandra Live Avatar Workspace Status

## Current Step

Planning the PRISM interactive-avatar goal and integration loops.

## Files

- `01-goal-and-loops.md` - product goal, architecture, loops, rollout path, and verification gates for Cassandra as a LiveAvatar-powered interactive PRISM experience.

## Current Recommendation

Use the official LiveAvatar sandbox/sample avatar first to prove rendering, session lifecycle, microphone, and video behavior. Do not build WebRTC/avatar plumbing from scratch.

For the real PRISM product, Cassandra must remain grounded in the existing PRISM/Hermes report-QA loop. LiveAvatar should be the face; ElevenLabs should be the voice; Hermes should remain the mind.

## Next Step

Implement a local-only proof that starts a LiveAvatar sandbox session through a backend-safe PRISM endpoint, then decide whether the first visible demo uses Embed/FULL mode for speed or LITE mode for the real Hermes-controlled loop.
