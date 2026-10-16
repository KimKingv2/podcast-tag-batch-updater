# Changelog

## v2.1

- Track number metadata now stores a single integer, without `/total`.
- Retains the per-show track assignment state so numbering continues after old audio files are deleted.
- Supports natural filename sort and modification-time sort for newly detected files.
- Keeps preview mode as the default and offers optional pre-write backups.

## v2.0

- Added persistent per-show track numbering.
- Added per-episode metadata overrides via `episodes.csv`.
- Added nested-folder discovery and log output.
