# Security Policy

The Mutation Testing Agent Toolkit installs and runs Gradle build logic and
agent instructions in user projects. Treat target project files, paths, and
tool output as untrusted; review generated changes and do not pre-approve
commands from unreviewed sources.

## Reporting a vulnerability

Please do not open a public GitHub issue for a suspected security problem.

Use GitHub's private vulnerability reporting for this repository when
available.

If that private reporting path is not available to you, do not disclose the
issue publicly. Contact the maintainers through a channel that does not expose
the vulnerability details and request a private reporting route.

Include as much of the following as you can:

- affected version, branch, or commit
- operating system, Java, Gradle, and Kotlin versions
- reproduction steps or proof of concept
- expected impact
- any known mitigations or workarounds

## Supported branches

Security fixes are coordinated with maintainers and applied to the default
branch and any release branches they identify as maintained. This policy does
not promise support for unmaintained branches or versions.

## Disclosure expectations

Give maintainers reasonable time to confirm the issue, prepare a fix, and
coordinate disclosure guidance before publishing full details. Reporters
should not disclose exploit details, credentials, or private project data in
public issues, logs, or pull requests.
