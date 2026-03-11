# Report Formatting

## Report Path

When `--file-output` is set, save the report to `{repo-root}/security-review-{timestamp}.md` where `{timestamp}` is `YYYYMMDD-HHMMSS` at scan time.

## Output Format

````
# Security Review — <project name or repo basename>

---

## Scope

|                                  |                                                        |
| -------------------------------- | ------------------------------------------------------ |
| **Mode**                         | default / deep / targeted                              |
| **Files reviewed**               | `file1.cairo` · `file2.cairo`<br>`file3.cairo` · `file4.cairo` |
| **Total in-scope lines**         | N                                                      |
| **Confidence threshold (0-100)** | 75                                                     |
| **Preflight findings**           | N deterministic hits                                   |

---

## Findings

[P0] **1. <Title>**

`Class: CLASS_ID` · `file.cairo:line` · Confidence: 92 · Severity: Critical

**Description**
<One paragraph: exploit path and impact.>

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```

**Required Tests**
- Regression test that reproduces the vulnerable path.
- Guard test that proves fix blocks exploit.

---

[P1] **2. <Title>**

`Class: CLASS_ID` · `file.cairo:line` · Confidence: 85 · Severity: High

**Description**
<One paragraph: exploit path and impact.>

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```

**Required Tests**
- Regression test that reproduces the vulnerable path.
- Guard test that proves fix blocks exploit.

---

< ... all findings ... >

---

## Findings Index

| # | Priority | Confidence | Severity | Title |
|---|----------|------------|----------|-------|
| 1 | P0       | [92]       | Critical | <title> |
| 2 | P1       | [85]       | High     | <title> |
|   |          |            |          | **Below Confidence Threshold** |
| 3 | P2       | [70]       | Medium   | <title> |
| 4 | P3       | [55]       | Low      | <title> |

---

> This review was performed by an AI assistant. AI analysis cannot verify the complete absence of vulnerabilities and no guarantee of security is given. Team security reviews, formal audits, bug bounty programs, and on-chain monitoring are strongly recommended.

````

## Rules

- Follow the template above exactly.
- Sort findings by confidence (highest first).
- Findings below threshold (confidence < 75) get a description but no **Fix** block.
- Do not re-draft or re-describe agent findings — print them directly.
- Insert the **Below Confidence Threshold** separator row in the Findings Index.
- Findings that fail FP gate must be dropped entirely and not reported.

## Finding Template (per finding)

Each finding must include:

- `[P{priority}] **{title}**`
- `Class: {class_id}` · `{file}:{line}` · `Confidence: {score}` · `Severity: {severity}`
- `Description:` one paragraph with concrete exploit path and impact.
- `Fix:` diff block (only for confidence >= 75).
- `Required Tests:` regression + guard test descriptions.

## Priority Mapping

- `P0`: direct loss, permanent lock, or upgrade takeover.
- `P1`: high-impact auth/logic flaw with realistic exploit path.
- `P2`: medium-impact misconfiguration or constrained exploit.
- `P3`: low-impact hardening issue.

## Deduplication Rule

When two findings share the same root cause, keep one:

- keep higher confidence,
- merge broader attack path details,
- keep a single fix/test block.
