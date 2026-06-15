# How to contribute

Thank you for investing your time in contributing to INSPECT-AI.

To get an overview of the project, please read the [README](README.md). For local setup, see [GETTING_STARTED.md](GETTING_STARTED.md).

## Issues

If you spot a problem or want to suggest a change, please search the [issue tracker](https://github.com/RIPE-Observatory/INSPECT-AI_open_source/issues) first. If a related issue does not exist, open a new issue on GitHub.

For workflow, check, or export changes, include the motivation, the affected part of the application, and the expected reviewer-facing behaviour.

## Proposing changes

INSPECT-AI supports the creation of research integrity assessment records from a human review workflow. Contributions are welcome when they improve reliability, usability, documentation, deployment, or the assessment workflow.

When proposing a change, please check that:

- reviewer-entered outputs remain separate from automated suggestions;
- changes to checks include the expected input, output, and reviewer-facing effect;
- changes to export behaviour remain compatible with RIPE-O and RIPE-KG where relevant;
- documentation is updated when setup, configuration, prompts, schemas, service flow, or check wiring changes;
- public examples or fixtures do not include private reviewer-identifying information.

If a change touches LLM-related prompts, schemas, service flow, or check wiring, update [LLM_GUIDE.md](LLM_GUIDE.md).

## Make changes locally

1. Fork the repository.
2. Create a working branch.
3. Make the focused change.
4. Run the relevant checks for the files you changed.

Useful checks include:

```sh
bun run lint
bun run typecheck
```

For tests:

```sh
bun run test
```

## Commit your update

Commit the changes once you are happy with them.

Always write a clear log message for your commits. One-line messages are fine for small changes.

## Pull request

When you are finished, create a pull request.

- Link the pull request to the issue it addresses.
- Describe the motivation for the change.
- Mention the checks you ran.
- Include screenshots or notes for reviewer-interface changes.
- Target the `main` branch.
