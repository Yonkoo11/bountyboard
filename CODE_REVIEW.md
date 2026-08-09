# Code Review

## July 30, 2026 rebuild

### Scope

- Broad opportunity discovery
- Evidence and freshness states
- Actionability ranking
- Static dashboard generation
- Responsive and accessible frontend
- GitHub Actions discovery and quality gates
- Documentation accuracy

### Resolved

- Unknown deadlines no longer render as `9999 days`.
- Scout candidates are published as unverified radar leads.
- Exact URL/name duplicates are collapsed in the generated view.
- Conservatively recoverable candidate deadlines are parsed; expired leads move
  out of the open view.
- Advertised opportunity pools are explicitly separated from expected earnings.
- Verification, application, eligibility, award type, individual award, and win
  probability fields were added to the data layer.
- Missing source, deadline, eligibility, and freshness are displayed as research
  tasks rather than hidden.
- The scheduled workflow now runs discovery, URL checks, tests, and generation.
- CI tests and rebuilds the site on pushes and pull requests.
- Setup instructions no longer reference nonexistent files.
- The dashboard has semantic landmarks, a skip link, visible focus states,
  accessible controls, 44px targets, responsive layouts, and reduced-motion
  support.
- External opportunity text is escaped and scraped multiline content is normalized.
- External source and submission links are restricted to absolute HTTP(S) URLs.
- Refresh jobs are serialized to prevent overlapping discovery runs from racing
  their generated commits.

### Final release gate

- Critical findings before final review: 1 unsafe-link protocol path.
- High findings before final review: 1 overlapping-refresh race.
- Critical findings remaining: 0.
- High findings remaining: 0.
- CodeRabbit CLI: installed, but automated review unavailable because the local
  CLI is not authenticated. Manual security review and repository checks were
  used as the documented fallback.

### Verification

- 16 automated tests pass twice consecutively.
- All Python files compile.
- Generated output passes `git diff --check`.
- Desktop and mobile browser smoke tests pass.
- Search and reset behavior pass across all generated opportunities.
- Category and evidence filters, reported-value sorting, and theme persistence pass.
- Browser console contains no errors.
- Mobile viewport has no horizontal overflow.

### Known limitations

- URL availability only partially verifies a lead; it does not prove eligibility,
  award terms, or application state.
- Win probability remains unknown until enough submission outcomes are recorded.
- Some sources can change markup or block automated requests.
- The current GitHub Pages site is read-only; triage and edits remain CLI/database
  operations.

## August 9, 2026 monitoring reliability release

### Scope reviewed

- Broad Devpost pagination across open and upcoming online events.
- Candidate retention, URL/name deduplication, retries, source-health history,
  last-run evidence, and degraded-source quality gates.
- Four-hour GitHub Actions refresh and local launchd path corrections.
- Generated hackathon data and verification-date handling.

### Automated review fallback

CodeRabbit CLI 0.3.5 was invoked, but it could not run because the local CLI is
not authenticated. The required manual security and correctness review was used
instead.

### Manual review results

- Critical findings remaining: 0.
- High-priority findings remaining: 0.
- Dynamic opportunity text continues to pass through the generator's HTML
  escaping and absolute HTTP(S)-URL validation; no new `innerHTML` or inline
  event-handler path was introduced.
- Network inputs are parsed as data and are not interpolated into shell commands.
- Subprocess call sites remain argument-array based; this release adds no
  `shell=True`, `eval`, or `exec` path.
- Request failures are retried, attributed to their source, persisted, and made
  visible to the quality gate instead of being treated as a successful empty run.
- The publish change detector includes untracked first-run operational files.
- Workflow permissions remain limited to repository contents writes needed for
  the generated Pages commit.
- No credentials, environment files, private keys, or tokens were added to the
  release diff.

### Verification

- 30 automated tests pass.
- Python compilation, JavaScript syntax, shell syntax, workflow YAML parsing,
  launchd plist validation, site generation, and `git diff --check` pass.
- `docs/styles.css` has no release diff; the established compact interface is
  intentionally preserved.

### Known limitations

- DoraHacks currently challenges or rejects the existing automated adapter. The
  gate intentionally marks that source degraded while still publishing results
  from working sources.
- Source discovery is broader, but individual eligibility, award terms, and
  deadlines still require source-level verification before committing build time.
- CodeRabbit authentication remains a local tooling setup task; manual review is
  the documented release fallback.

## August 9, 2026 HackList cross-check adapter

- Uses HackList only for discovery and retains the canonical Apply URL.
- Does not inherit third-party verification or infer dates from relative countdowns.
- Rejects non-HTTP(S) Apply links and deduplicates repeated canonical URLs.
- Treats a zero-result or broken HackList parse as degraded coverage.
- Fixture tests cover parsing, URL safety, URL deduplication, conservative prize
  extraction, unknown deadlines, and the source-health gate.
- Live read-only validation found 33 listings: 5 already recognized and 28 gaps.
- Critical findings remaining: 0. High-priority findings remaining: 0.
