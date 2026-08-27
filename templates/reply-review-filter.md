---
name: reply-review-filter
description: Shared discriminator for separating real PR reviews from the single-comment reviews GitHub creates for every review-thread reply — for any skill deciding "have I already reviewed this PR?" from a review list.
type: template
---

## Why this exists

GitHub has no standalone thread reply. Every reply to a review thread is wrapped in its own `PullRequestReview` — state `COMMENTED`, one comment, submitted immediately — the same object type a real review is, authored by the same identity. That is the platform's model, identical to what the web UI's **Reply** button produces; nothing a skill does can avoid creating them.

So any selector that asks "have I already reviewed this PR?" by listing reviews under your login counts every reply as a review. Measured on `flaviosv/applyr#16` after one `fix-review` run: **34 reviews under one login — 1 real, 33 reply artifacts.** Two selectors break on that, both silently:

- A "your latest review's verdict" test reads the newest reply instead of your actual verdict, so a PR with open change requests stops qualifying the moment it was fixed once.
- An "any review by you means reviewed" test hides a PR you never actually reviewed, permanently, because you once replied on someone else's thread.

## The discriminator

A review is a **reply-review** when **both** hold:

1. its `body` is empty, and
2. every one of its comments has a non-null `replyTo`.

Both conditions are required. Empty `body` alone is wrong: a real review created via `addPullRequestReview` and submitted with `event: COMMENT` — exactly what `complete-review` publishes and `build-feature` submits — also has an empty body. On PR #16 the genuine 33-finding review has `body_len 0`; a body-only test discards it and keeps nothing.

A review carrying more than 100 comments is never a reply-review (they hold exactly one), so a truncated comment page must never decide the answer — treat `comments.totalCount > 100` as real without inspecting further.

## The query

```
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!, $me: String!, $cursor: String) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviews(first: 100, after: $cursor, author: $me) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            state
            submittedAt
            body
            comments(first: 100) { totalCount nodes { replyTo { id } } }
          }
        }
      }
    }
  }' -f owner="<owner>" -f repo="<repo>" -F pr=<pr number> -f me="<your login>"
```

Page until `hasNextPage` is false — never a bare `last: N`. Reply-reviews accumulate at the end of the list, one per thread, so a fixed tail returns nothing but artifacts: on PR #16, `last: 30` yields 30 reply-reviews and misses the real review entirely, turning a reviewed PR into an unreviewed one.

REST cannot do this check — `GET /repos/{owner}/{repo}/pulls/{n}/reviews` returns no comment data, and `replyTo` is the whole discriminator.

## Applying it

Drop every reply-review first; what remains is your real review history. Judge only against that — the latest of it for a "what verdict do I currently hold?" test, its emptiness for a "have I reviewed this at all?" test. A reply-review is never evidence of a verdict; it is evidence that you replied.

Verified against `flaviosv/applyr#16` on 2026-08-27: 34 reviews → 33 reply-reviews, 1 real, with the latest-overall and latest-real reviews correctly diverging.
