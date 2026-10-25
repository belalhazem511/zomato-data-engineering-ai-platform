# Security policy

Please do not report credentials or other sensitive information in a public issue. Contact the repository owner privately through the GitHub account associated with this project.

If a secret is exposed, revoke or rotate it immediately, remove it from all reachable Git history, and investigate affected systems. `.gitignore` does not remove secrets that were already committed.

Raw datasets are excluded because they may contain personal or sensitive information. See `docs/security.md` for project-specific controls and known risks.
