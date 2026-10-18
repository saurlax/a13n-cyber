# Specifications

This directory defines the accepted architecture and behavior of a13n Cyber. Specifications own system contracts; README owns user instructions, and tests verify implementations against those contracts.

## Document Catalog

| Document | Owning contract |
| --- | --- |
| [00-architecture.md](00-architecture.md) | Components, dependency direction, and execution boundaries |
| [01-cli-and-agent.md](01-cli-and-agent.md) | CLI, model configuration, agent composition, workspaces, and limits |
| [02-tsecbench.md](02-tsecbench.md) | Platform adapter, challenge lifecycle, tools, completion, and cleanup |
| [03-container-toolkit.md](03-container-toolkit.md) | Container tools, packaged skills, inventory, and offline verification |
| [04-rea.md](04-rea.md) | Optional REA MCP, upstream skills, Ghidra packaging, and offline verification |

## Specification Discipline

Assess the need for a specification before every implementation change. Changes to public interfaces, configuration, component responsibilities, external integrations, lifecycle, persistence, or security boundaries update the owning contract before implementation. Private refactors and fixes that restore an existing contract do not require a new document.

Specifications describe accepted behavior directly in present tense, with explicit ownership and observable outcomes. Each contract has one owning document; other documents link to it rather than maintaining competing definitions. Use numbered topic files, and add a subsystem directory with its own catalog only when its size warrants one.

Do not store RFC drafts, alternatives, open-question logs, implementation checklists, roadmaps, status matrices, transcripts, or temporary handoff notes here. Discuss unresolved decisions with the user or in an authorized issue. Update contracts, code, tests, and user documentation together. Superseded behavior is replaced in place; Git records history.

This model follows [Agent Foundation's specification discipline](https://github.com/converge-ai-labs/agent-foundation/blob/main/spec/repository-model.md#specification-discipline), scaled to a single Python application. It does not require external issue creation or publication for local implementation.
