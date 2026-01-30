---
name: sync-official
description: Compare with official ImagingDataCommons/idc-claude-skill and generate improvement reports
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---

# Sync Official Skill

Compare this repository with the official ImagingDataCommons/idc-claude-skill and manage improvements systematically.

## Commands

### `/sync-official update`

Update the local reference copy of the official skill:

```bash
cd _reference/idc-claude-skill && git fetch origin && git pull origin main
```

Then report the current commit hash for tracking.

### `/sync-official report`

Generate a comparison report between this repo and the official skill:

1. Read both versions of each comparable file
2. Identify differences and improvements
3. Review local-only files for simplification opportunities
4. Generate `_sync-report.md` with prioritized improvements

### `/sync-official apply`

Process improvements from `_sync-report.md` one at a time:

1. Read the report and find the first pending improvement
2. Implement the improvement
3. Create an atomic commit
4. Update the improvement status to `[x] Done`
5. Stop and report completion (user runs again for next improvement)

## Reference Locations

### Local Files
- `SKILL.md` - Main skill documentation
- `references/` - Extended documentation

### Official Reference
- `_reference/idc-claude-skill/` - Local clone of official skill
- Compare: `SKILL.md` ↔ `_reference/idc-claude-skill/SKILL.md`
- Compare: `references/*.md` ↔ `_reference/idc-claude-skill/references/*.md`

## Comparison Files

| Local | Reference |
|-------|-----------|
| `SKILL.md` | `_reference/idc-claude-skill/SKILL.md` |
| `references/bigquery_guide.md` | `_reference/idc-claude-skill/references/bigquery_guide.md` |
| `references/dicomweb_guide.md` | `_reference/idc-claude-skill/references/dicomweb_guide.md` |
| *(none)* | `_reference/idc-claude-skill/USAGE.md` |

## Local-Only Files to Review

These files don't exist in official but should be reviewed for alignment with official patterns:

| File | Review Focus |
|------|--------------|
| `references/index_tables.md` | Align with official table documentation patterns |
| `references/sql_patterns.md` | Ensure patterns match official examples |
| `references/use_cases.md` | Check if official has simpler approaches |
| `references/analysis_integration.md` | Verify integrations match official recommendations |
| `references/memory_management.md` | Check if CLI approach is simpler |
| `references/data_validation.md` | Review if official has validation guidance |
| `scripts/batch_download.py` | **Consider replacing with `idc download` CLI** |
| `scripts/validate_download.py` | Check if pydicom patterns match official |
| `tests/` | Ensure test patterns align with official examples |

### Key Principle: Prefer CLI over Custom Code

The `idc-index` package includes CLI commands that may replace custom scripts:

```bash
# Download entire collection
idc download rider_pilot --download-dir ./data

# Download specific series by UID
idc download "1.3.6.1.4.1.9328.50.1.69736" --download-dir ./data

# Download from manifest file (auto-detected)
idc download manifest.txt --download-dir ./data
```

**Improvement types for local-only files:**
- **Simplify**: Replace custom code with CLI/official patterns
- **Align**: Update to match official conventions
- **Fix**: Correct patterns that differ from official best practices

## Comparison Criteria

### What to Compare
- API patterns and code examples
- Table schemas and column references
- Best practices and recommendations
- Error handling approaches
- Documentation structure

### Priority Levels

| Priority | Description |
|----------|-------------|
| **High** | Bug fixes, API changes, security issues, missing critical documentation |
| **Medium** | New features, improved examples, new patterns |
| **Low** | Formatting, minor wording changes, additional examples |

### Difficulty Levels

| Difficulty | Description |
|------------|-------------|
| **Easy** | Simple text changes, single-file, copy-paste |
| **Medium** | Adaptation needed, multiple related changes |
| **Hard** | Major restructuring, significant rewriting |

## Report Format

When generating `_sync-report.md`, use this structure:

```markdown
# Sync Report

Generated: [timestamp]
Reference: ImagingDataCommons/idc-claude-skill @ [commit hash]

## Summary

- Total improvements: N
- By priority: High (N), Medium (N), Low (N)
- By source: Official sync (N), Local enhancement (N)

## Improvements

### 1. [Brief Title]

- **Status**: [ ] Pending
- **File**: `path/to/file`
- **Priority**: High|Medium|Low
- **Difficulty**: Easy|Medium|Hard
- **Type**: New Content|Update|Fix|Simplify|Align
- **Source**: Official sync|Local enhancement

**Description:**
What needs to change and why.

**Reference content:** (if from official)
The relevant content from the official skill.

**Action:**
Specific steps to implement this improvement.

---

### 2. [Next improvement...]
```

## Apply Workflow

When running `/sync-official apply`:

1. **Read Report**: Load `_sync-report.md`
2. **Find Pending**: Locate first improvement with `[ ] Pending` status
3. **Implement**: Make the required changes
4. **Commit**: Create atomic commit with format:
   ```
   sync: [brief description]

   Improvement #N from sync report
   Priority: [priority]
   Source: [official idc-claude-skill | local enhancement]
   ```
5. **Update Status**: Change `[ ] Pending` to `[x] Done` in report
6. **Report**: Tell user what was done and how many remain

## Reference Links

### Official IDC Resources
- [idc-claude-skill](https://github.com/ImagingDataCommons/idc-claude-skill) - Official IDC skill
- [idc-index](https://github.com/ImagingDataCommons/idc-index) - Python package
- [IDC Documentation](https://learn.canceridc.dev/) - Learn IDC

### Related Skills
- [mhalle/idc-skill](https://github.com/mhalle/idc-skill) - Alternative IDC skill
- [claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) - 140+ scientific skills

### Claude Code Documentation
- [Skills](https://docs.anthropic.com/en/docs/claude-code/skills) - Skills documentation
- [Sub-agents](https://docs.anthropic.com/en/docs/claude-code/sub-agents) - Sub-agents guide
- [Memory](https://docs.anthropic.com/en/docs/claude-code/memory) - Memory and CLAUDE.md
