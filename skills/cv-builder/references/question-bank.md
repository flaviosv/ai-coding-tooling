# Question Bank

The extraction script for Phase 2. Work it **one question at a time** through the grilling skill, per role, oldest → newest (unless the person prefers newest-first). Goal: extract as much as possible into the catalog — depth over speed. Skip anything already answered by a seed context; go deeper instead of re-asking.

---

## Per-role questions

**A. Framing**
1. Company name + one line on what it does, its market, and scale.
2. Your title, level, and employment type (FT / PT / contract / freelance) + reporting line.
3. Why were you hired / what was the core mandate?

**B. Work (STAR)**
4. The 2–4 things you are proudest of or that mattered most — each becomes a STAR block.
5. For each: Situation (the problem), Task (your responsibility), Action (what *you* did), Result (measurable outcome).
6. The hardest technical problem, and how you solved it.
7. What you built/owned end-to-end vs. contributed to.

**C. Scope & scale (get numbers)**
8. Team size; did you lead or mentor anyone? Technical or managerial leadership?
9. System scale — users, concurrent traffic, requests/day, data volume, revenue processed, uptime.
10. Any before/after metric — latency, cost, conversion, deploy time, bug rate, sales.

**D. Deep tech-stack (priority)**
11. Languages (+ versions), frameworks, databases, infra, libraries — and *what each was used for*.
12. Integrations (ERPs, gateways, search, APIs, queues) — which, and how complex.

**E. Impact & growth**
13. Business impact of your work (revenue, cost, awards, customer outcomes).
14. What you learned / how you grew here; promotions.
15. Anything notable not yet captured (awards, firsts, crises handled).

---

## F. Job-tailoring probes (Job-Tailoring Mode)

Not a full re-run of the extraction interview — grill **only** what the match/gap analysis leaves ambiguous, one question at a time.

1. When two catalog items could both satisfy a JD requirement: which should lead, and why (recency, closer scope match, stronger metric)?
2. When a JD requirement has zero support in `experiences.md`: is there real but undocumented experience here, or is it an honest gap?
3. When the JD's seniority/focus differs from the base CV's positioning: does the person want to reposition for this application (e.g. lead with a different specialization), and how far?
4. When a catalog bullet that lost the base CV's page budget now looks JD-relevant: confirm it should resurface here.

## Cross-cutting guards

- **One question at a time.** Multiple questions at once overwhelm and thin out the answers.
- **Always offer a recommended/default answer** for the person to react to — reacting is easier than recalling from scratch.
- **Honesty guards:** capture ownership precisely (built / co-built / contributed / team's); never invent metrics; mark estimates `~` and add to **To verify**; integrity-flag any skill or number the person could not defend in an interview.
- **Deep tech-stack priority:** probe the stack as hard as the achievements — it is what recruiters filter on and what interviews open on.
- **Write as you go.** Every answer lands in `experiences.md` immediately (STAR block, stack, scope, draft bullet), and the progress tracker + `Resume from:` marker update after each answer so the session is always resumable.

## Review sweeps (Phase 3)

After the roles are mined, prompt the person's memory — it is the bottleneck:
- **Forgotten-wins sweep:** awards, recognition, promotions, extra/side projects, "first to introduce X", crises handled.
- **Scale-number sweep:** any user/traffic/data/revenue figures they can now recall with a nudge.
- Leave a number out rather than guess. Record every resolution in the Decisions log.
