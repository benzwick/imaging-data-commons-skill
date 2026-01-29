# Imaging Data Commons Skill

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) for querying and downloading public cancer imaging data from the [NCI Imaging Data Commons](https://portal.imaging.datacommons.cancer.gov/).

## Installation

Add this skill to your Claude Code project:

```bash
# Clone to your .claude/skills directory
cd your-project/.claude/skills
git clone git@github.com:benzwick/imaging-data-commons-skill.git imaging-data-commons

# Or symlink from another location
ln -s /path/to/imaging-data-commons-skill .claude/skills/imaging-data-commons
```

## Dependencies

Install the required Python packages:

```bash
uv sync
```

## Usage

Once installed, Claude Code can use this skill to:

- Query IDC metadata for CT, MR, PET, and pathology images
- Download DICOM files with license filtering
- Visualize images in browser
- Validate downloaded data integrity

Example prompts:
- "Find all chest CT scans in the NLST collection"
- "Download brain MRI data with CC-BY license only"
- "How many segmentations are available for lung cancer?"

## Running Tests

```bash
cd imaging-data-commons-skill
uv sync --extra test
uv run pytest
```

## Structure

```
├── SKILL.md              # Main skill documentation (read by Claude)
├── references/           # Detailed reference documentation
├── scripts/              # Utility scripts (batch_download.py, validate_download.py)
└── tests/                # Pytest test suite
```

## License

MIT License. IDC data has individual licensing (CC-BY, CC-NC) - see SKILL.md for details.

## Resources

- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [IDC Portal](https://portal.imaging.datacommons.cancer.gov/)
- [IDC Documentation](https://learn.canceridc.dev/)
