# Schema Development Guide

---

## I. Guiding Principles

### PRs are communication artifacts
A PR should always make its **intent, scope, and status** explicit.
The diff alone is not sufficient context.

### Uncertainty should be surfaced early
Open questions, design concerns, or architectural uncertainty should appear early in the PR—not discovered late during review.

### Splitting and closing PRs is normal
Large, blocked, or outdated PRs should be split or closed without stigma.
Closing a PR is a decision, not a failure.

### Momentum is a shared responsibility
Authors and reviewers are jointly responsible for moving PRs toward a clear outcome.

### Explicit decisions over silent waiting
A stalled PR should always converge toward a visible decision: proceed, split, block, or close.

---

## II. Common Challenges

- **Stale or silent PRs:** Remain open without activity, status, or clear ownership.
- **Unclear or growing scope:** Scope expands during review or design uncertainty surfaces late, making review slow and difficult.
- **Blocked PRs without visible blockers:** Dependencies on other work, people, or decisions are not made explicit.
- **Loss of context across PRs and repositories:** PRs, issues, and follow-ups are not consistently linked.
- **Limited visibility into parallel work:** Team members are unaware of related or overlapping work.
- **Reviews that do not advance toward a decision:** Feedback acknowledges work without clearly approving, blocking, or requesting concrete changes.
- **Reluctance to close or rework PRs:** Remain open even when direction changes or scope becomes unclear.

---

## III. Branching, Conflict Resolution & PR Maintenance

### Branching Model

- Development primarily happens on **short-lived branches** created from `develop`.
- Branching off a working branch is acceptable during the draft phase (e.g. to try alternatives or propose fixes).
- Branch names should use a short, hyphen-separated description.
- Each branch should address **one logical change only**.

---

### Conflict Resolution: Rebasing and Merging

Both `git rebase` and `git merge` are valid tools. The choice should be **pragmatic**.

**Default guidance**
- Rebasing onto `develop` is the default recommendation, especially for newer contributors.
- Merging `develop` into a feature branch is also acceptable and sometimes preferable.

**Rebasing is often easier when**
- PRs are small or medium-sized
- Conflicts are limited
- A clean, reviewable diff matters

**Merging may be preferable when**
- Branches are long-lived
- Conflicts are complex or repeatedly reoccur
- Preserving the development sequence aids understanding
- The branch already integrates many changes from `develop`

Because PRs are merged via **Squash & Merge**, neither approach affects the final history of `develop`.

**Key expectation**
A feature branch should be reasonably up to date with the target branch (`develop`) so that the PR can be reviewed and tested against current code, not just merged without conflicts.

---

### PR Maintenance Expectations

- Keep PRs reasonably up-to-date with `develop`.
- Avoid letting unresolved conflicts accumulate.
- If maintenance becomes complex or reveals deeper issues:
  - Split the PR
  - Mark it as blocked (with explanation)
  - Close and reopen a cleaner PR

---

### Merge Strategy

- All PRs are merged via **Squash & Merge**.
- Each PR results in one atomic commit.
- Clear traceability is maintained: commit → PR → issue.

---

## IV. Pull Requests

### PR Scope

A PR should be:
- Small (reviewable in ~30 minutes)
- Focused (one clear purpose)
- Self-contained (code, tests, and documentation aligned)

---

### PR Description

Each PR should include:
- What changed
- Why it changed
- How it was tested
- Links to relevant issues (e.g. `Fixes #123`)
- Screenshots or examples where relevant, e.g. PRs pertaining to front-end features.

A communication-focused PR template is used to support this.

---

### Review Expectations

**Before requesting human review**
- Request Copilot review where applicable.
- Keep the PR in **Draft** until ready for full review.
- Exceptions are acceptable when early conceptual or architectural feedback is needed.

**Author responsibilities**
- Ensure CI passes before review
- Respond promptly to feedback
- Keep commits small, focused, and with a clear and concise commit message
- Facilitate the review by communicating relevant context or desired focus areas to the reviewer.
- Use best judgement to choose reviewer/s with relevant knowledge for PR focus areas.

**Reviewer responsibilities**
- Review within an agreed timeframe
- Focus on correctness and clarity
- Clearly distinguish blocking vs non-blocking feedback
- Actively advance PRs toward a decision

**Reviewer responsibilities**
- Review within an agreed timeframe
- Be thoughtful; do not rush
- Focus on correctness, clarity, and intent
- Address any explicitly flagged concerns
- Clearly distinguish blocking vs non-blocking feedback
- Actively advance PRs toward a decision

---

## V. Code Quality, Testing & Documentation (Baseline)

The following are baseline expectations:

- Use meaningful commit messages, preferably written in the imperative form (e.g., `Add validation for empty input` or `Refactor parser control flow`)
- Separate refactors from behavioral changes
- Follow established linting and formatting tools
- Add or update tests when behavior changes
- Update documentation when APIs or behavior change

---

## VI. Structural Conventions

### Implemented Conventions

- Communication-focused PR template
- PR lifecycle labels:
  - `pr:blocked`
  - `pr:stale`
  - `pr:follow-up-needed`
  - `pr:needs-decision`

### Coordination Mechanisms

- PRs should explicitly link related issues and other PRs.
- Follow-up work should typically be tracked explicitly by creating new issues, not left as implicit TODOs.
- Responsibility for follow-up issues may vary. Assignments should be used wherever possible. Otherwise, the author/project lead share responsbility for following up. The author of in-code TODO comments is responsibile for keeping track and following up in that case.
- For multi-step changes, a **super-issue** (labeled `SUPER ISSUE`) can be used to track progress across multiple PRs via a checklist.
- For broader-scoped, longer-term, or cross-repository work, project boards may be used to provide shared visibility.
- When a PR cannot be easily unblocked via direct communication between author and reviewer, a dedicated moment (meeting or agenda item) should be used to unblock PRs collaboratively.

---

## VII. Evolution of This Guide

This guide is a living document.

Improvements should be proposed via pull requests, discussed briefly with the team, and refined based on practical experience.
