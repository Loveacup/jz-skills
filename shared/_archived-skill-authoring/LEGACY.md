---
name: skill-authoring
description: Create, revise, import, or audit Agent Skills; govern a named skill collection or agent instruction files such as AGENTS.md. Not for ordinary coding or executing a skill's subject task.
type: routine
version: 6.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, progressive-disclosure, governance]
    related_skills: [skill-creator]
---

# Skill Authoring

Help an agent do a class of work better by supplying useful expertise, direction and resources. A skill should amplify the model's reasoning, research and adaptability, not replace them with an itinerary.

## Start with the work

Understand the user's intended result and what the agent needs to accomplish it. Inspect the existing skill and its maintained source before proposing missing capabilities; runtime copies can lag or contain local adaptations. Use the target's source record to resolve ownership when copies differ.

Use your judgment to choose the approach. Draw on model knowledge for familiar connective work; inspect files, tools and primary sources for facts that need verification. Research a consequential unknown, compare alternatives and seek counterevidence when they can change the design. A small correction needs a small correction, not a research project. For a substantive redesign, investigate the whole skill and relevant evidence, agree on direction, scope and tasks with the user, then edit; an assessment request is not implementation authorization.

**Wording-only edits:** make the focused change, check meaning and affected links, then finish. For substantive work, keep the result and its important acceptance conditions clear; choose the amount of planning and validation the task warrants.

Before changing an existing skill's behavior, establish what it must keep delivering from its existing requirements and actual behavior. A small skill can keep that baseline in its body or existing notes; do not create a separate requirements file just to begin an edit. This maintained family keeps its existing [core requirements](references/core-requirements.md). Choose traceability proportional to the work as [Author](references/author.md#keep-the-skill-traceable) explains.

## Design for judgment

Give the consuming agent the goal, task-specific knowledge, useful decision cues and a way to recognize a good result. Explain why a method works and when it applies. Let the agent choose tools, sequence ordinary steps, retrieve current information and adapt methods to the situation.

Keep exact interfaces, required output contracts and necessary safety constraints concrete. Recommended methods are adaptable; explicit user requirements and applicable host rules remain binding. More detail earns its place when it supplies missing expertise or prevents a real failure, not merely because it makes the document look complete.

Write for complete outcomes with the least delivery and maintenance burden, not the fewest lines. Prefer existing capabilities; add structure for a current consumer, obligation or demonstrated gap. Judge safeguards by what they detect and how rejection, recovery or diagnosis changes the result. Use the task's actual exposure and consequences, not hypothetical future users, to choose the engineering burden. Repair the instruction causing unnecessary work rather than stacking counter-rules. These are decision cues, not a new checklist, proof file or review stage.

Make verification answer a consequential question and reuse evidence that still applies to the final state. Repeat for changed behavior, failed checks, unresolved material uncertainty or explicit requirements, not to demonstrate diligence. Finish when the requested result and proportionate evidence are complete. State meaningful limitations beside the claims they qualify; omit ritual cautionary footers and internal process narration that do not help the reader decide or act.

## Reach for depth when useful

- Designing or substantially improving a skill: [Author](references/author.md).
- Diagnosing failures or deciding whether a change helps: [Evaluate](references/evaluate.md).
- Overlap, discovery or responsibility across a named library: [Collection governance](references/collection-governance.md).
- Improving AGENTS.md or equivalent instruction surfaces: [Agent instructions](references/agent-instructions.md).
- Reconciling upstream, maintained and local copies: [Import](references/import.md).
- Applying, deploying, publishing or retiring an artifact: [Release](references/release.md); [Privacy](references/privacy.md) when content crosses a trust boundary.
- Local ownership, generated entrypoints or installation bindings: [SkillHub adapter](references/skillhub.md).
- A "new model" audit of accumulated instructions: [Collection governance](references/collection-governance.md) plus [Agent instructions](references/agent-instructions.md) over the targets the user names, not a scan of every installed file.

These are resources for the question at hand, not a sequence to complete. [Research notes](references/research-notes.md) and [changelog](references/changelog.md) provide background, not additional gates.

## Carry the work through

Complete the requested artifact and inspect whether it actually serves the task. Preserve unrelated work and legitimate local adaptations. Continue inside the authorized scope; ask when a material decision or missing permission really changes the next action. When replacing a writer on the same scope, obtain affirmative exit or lock/lease-release evidence first; timeout or silence alone does not show that writing stopped.

Creation or review does not grant permission to publish, delete, repoint a consumer, change credentials or deploy elsewhere. Follow the named action's authority and the conditional release guidance. Missing required evidence leaves that claim blocked, while independent work can continue. Changing this skill does not waive the rules currently governing the session.

Describe what changed, what was actually checked and any uncertainty material to using the result. Prefer repairing an implicated idea or resource to accumulating another warning after every run. Record behavior changes through the skill's existing history or an appropriately small note; update requirements when their meaning changed, as [Author](references/author.md#keep-the-skill-traceable) describes.
