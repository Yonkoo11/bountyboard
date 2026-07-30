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
