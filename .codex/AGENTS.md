# AGENTS.md

## Sub-agents

- Do not interrupt an active sub-agent just because it is quiet or has been running for a while.
- Before any interrupt: `wait(...)` first, then try a non-interrupting status request.
- Interrupt only if the user asks, there is clear evidence of failure/blocking, or continuing would be unsafe or conflict with new instructions.
- If a sub-agent is likely close to producing a file, patch, JSON, test result, or command result, prefer waiting for that artifact.
- If you interrupt a sub-agent, state the reason and the evidence.
- If the interruption was premature, acknowledge that progress may have been lost and retry with less interference.
