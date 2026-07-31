# Trailhead — Pitch Script

Spoken script, roughly 3 minutes plus the demo. Plain text is what you say. *Italics are stage directions.*

---

## 1. The problem

Everyone in this room has lived it: you join a new team, pick up a task in code you have never touched, or come back to your own project after six months — and you are lost.

Your options: docs that went stale months ago, a teammate's whole day, or an AI chatbot that will explain anything — while nothing checks whether the explanation is true.

Getting an explanation of code is easy now. Trusting one is not.

## 2. What we built

Trailhead. You point it at a project's code and it generates a single web page: a walkthrough that teaches that project to someone who has never seen it — from "what is this project" down to setting it up and running its tests. Today it reads Python projects; that is a scope decision for the hackathon, not a limit of the design.

It opens in a browser with no server, no login, and no internet connection. You can email it to a new joiner, or keep it stored alongside the code it describes.

Here is the difference from other AI documentation tools: **the AI writes the prose, but ordinary code checks every fact — and the page shows its evidence for every claim it makes.**

## 3. How the checking works

The AI is only allowed to state a fact if it also hands over a word-for-word quote of the code it is describing.

Our system takes that quote, finds it in the real file, records the file and line numbers, and takes a fingerprint of those exact lines.

After the AI is done, the checker re-reads everything. If a quote cannot be found in the file, word for word, that sentence is deleted. Not flagged — deleted. Sentences the AI could not back with a quote are visibly marked as unverified — they are never allowed to look proven. And the page shows the count: how many claims the AI made, how many were kept, how many were deleted, and why.

*(One detail for the engineers: we never ask the model for line numbers — models count badly, but they copy well. Requiring verbatim quotes and resolving the line range in code is the difference between roughly a 40% deletion rate and 3%.)*

Same rule for commands. When the page shows what happened when you run "set this project up", we actually ran that command while the page was being built. What you see is the real result — success or failure, exactly as it happened, with real timings. A failing command is shown failing, under a banner that says so.

And the reason you can trust the checking: the system has five stages, and exactly one of them touches an AI. Everything that verifies anything is plain, predictable code — it gives the same answer every time. A model is never asked to mark its own homework.

## 4. Demo

# 🎬 [ DEMO HERE ]

## 5. Why this matters beyond onboarding

Three things fall out of this design.

**One — staleness becomes visible.** Every claim carries a fingerprint of the code it describes. Re-checking the page against the code is a single command, so a team can plug it into the automatic checks that already run on every code change: the moment someone changes code the walkthrough describes, a check fails and the whole team knows. Docs that rot loudly instead of silently.

**Two — the AI's output is auditable.** In this firm, saying "an AI wrote our internal docs" invites one question: how do you know it is not making things up? Our answer is a ledger, not a shrug: every claim the model made, every claim kept, every claim deleted — each deletion listed with its file and the reason. We can show exactly what the model said, and exactly what we refused to publish.

**Three — it is a file, not a service.** Nothing to host, nothing to keep running, no per-user AI cost, and it never sends anything anywhere. That also makes it easy to approve.

## 6. Conclusion

The model writes the prose. The machine checks the facts.
Every sentence on the page shows its evidence, is marked as unverified — or is gone.
