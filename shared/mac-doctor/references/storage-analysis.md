# Bounded storage attribution

Use this when storage pressure needs attribution beyond the existing cleanup catalogue. `check`, `score`, history, security/hardware/network/devenv, collector/watchdog, cleanup approval and renewal capabilities remain available. This command is an additional diagnostic, not a replacement for the rest of mac-doctor.

## Commands

Run from the resolved skill directory:

```sh
scripts/mac-doctor storage analyze --json
scripts/mac-doctor storage analyze --root /absolute/selected/directory --budget-sec 15 --min-mb 10 --json
scripts/mac-doctor storage analyze --root /absolute/selected/directory --html /absolute/new-report.html --json
```

Default scope: OS-account home, Library, Caches, Containers, Group Containers, Application Support, Downloads, Developer and `/Applications`. The account path uses `macdoctor.paths.account_home`, not a redirected cron profile HOME. Explicit `MAC_DOCTOR_HOME` remains the existing supported override; no new state directory or config is created. Use repeatable roots for a particular opaque container, application cache or large developer directory after inspecting the first result.

Defaults: 30 seconds of command budget, 3 seconds maximum per subprocess, 200 immediate entries per root, 50 MiB minimum known size and five ranked hotspots. Limits are configurable within `--help`; budget maximum is 120 seconds, roots maximum 32. When capped, narrow the next root rather than silently extending an all-machine scan. Filesystem metadata operations themselves can block on a stalled filesystem: this is bounded command dispatch, not an OS-level hard deadline or filesystem sandbox.

Each selected root enumerates one level, while fixed-argv `/usr/bin/du -skx` measures child subtrees recursively on that filesystem. Symlinks, other-filesystem children and special files are visible exclusions. Planned detailed roots expand separately instead of repeatedly measuring broad aggregates. Duplicate path roots and successfully observed same-inode aliases are not ranked/measured twice. It is not a content search, malware scanner or exact clone-block accounting engine.

## Reading the JSON

- `system.apfs`: container metadata from `diskutil info -plist /System/Volumes/Data`. Status is separate from directory coverage. Missing metadata stays unknown; zero free bytes is a valid critical capacity observation, not missing data.
- `groups`: observed children, retained unknown/partial/excluded/expanded entries, small-item filter counts and omission reasons. Default optional absent directories are marked absent; an explicitly requested missing directory is incomplete.
- `top_consumers`: known, above-threshold, pairwise non-overlapping observed hotspots. Detailed requested groups replace broad aggregates in this ranking. Not the largest files everywhere, not a global inventory and not a list of safe deletion targets.
- `coverage`: complete means selected roots were enumerated/measured under the declared limits/exclusion policy. It does not mean full-disk visibility or health PASS. Entry/budget exhaustion and failed/unreadable measurements make it false. Unknown values are null, never invented zeroes.
- `accounting.additive:false`: nested groups overlap. Do not sum their sizes, compare their sum against the APFS container or manufacture a category pie chart from it. APFS clones/shared blocks make nominal allocated bytes different from physical reclaimability. `estimated_reclaimable_bytes` remains null until a separate supported cleanup assessment.

`du` output with nonzero exit is not a complete size: a parsed number is retained only as `observed_lower_bound_bytes`; the item remains partial with `size_bytes:null`. Permission/error text is reduced to fixed reason codes, not dumped from stderr.

Only system container-identity metadata may be read for attribution: an ordinary, bounded `.com.apple.containermanagerd.metadata.plist`, extracting `MCMMetadataIdentifier` only. No user documents, chat databases, browser profiles or model contents are read. Ownership is unknown when metadata is unavailable; do not guess an app from a UUID.

Exit 0: selected scan completed under policy. Exit 1: usable partial report with explicit gaps. Exit 2: invalid input, unsupported platform or failure to create the requested report. Check JSON statuses alongside exit codes.

## Decisions, not automatic green labels

Cache-like naming is not cleanup authorization. `.cargo` can contain toolchains, `.docker` persistent volumes, `.gradle`/`.m2` settings, `.cache` production models, and app/group containers user databases. These stay protected-review. Even known pip/uv/npm download caches and Xcode DerivedData are only potentially regenerable candidates: inspect exact scope and active use, then use the existing separately authorized plan/apply or reviewed owner-authorized workflow. No change to SAFE/CAUTION/REPORT/NEVER catalogue gates.

For the report: state the dominant observed consumers, measurement basis, coverage gaps and useful next selected root. Recommend app-native storage controls for managed app data. Do not claim an unknown amount of space can be released, advise a broad cache purge, or turn age/extension/size into disposal permission.

## Offline report

`--html` requires an absolute **new** output filename. The artifact is created with mode 0600 and exclusive creation; an existing file/symlink is refused, never overwritten. It is local static HTML with collapsible root sections, escaped paths and strict CSP; no scripts, external assets, browser auto-open, HTTP server, cleanup button or command executor. Writing this explicitly requested artifact is the only additional write performed by analysis.

Reports can reveal private directory names and app ownership. Keep them in the approved local output area; sharing/upload needs user authorization. If the requested output cannot be written, no cleanup occurs and the command returns 2.

## Cron-worker use

The deployed cron-worker skill link and compatibility shims resolve the existing shared canonical source. Do not fork a second copy, install a deletion server, register more jobs, change cadence or restart services to gain this feature. Existing collector/watchdog jobs keep their lightweight behavior. For a concrete storage alert or an explicit user request, a triage agent can select a narrow root and use this command within the task's read permissions; do not schedule a full-home du walk every tick. Human-facing output remains concise and evidence-based.

## Source and adaptation

Inspired by [KKKKhazix/khazix-skills storage-analyzer](https://github.com/KKKKhazix/khazix-skills/tree/322346ded8129436b3f64707789a73e732ae24d9/storage-analyzer): grouped attribution, opaque-container ownership investigation, top consumers and the overview→diagnosis→recommendations report flow. Implementation is independent; upstream scanner, templates and deletion server were not copied. Deliberately excluded: blanket green cache labels, HOME-only path resolution, swallowed partial failures, overlapping category totals and default interactive deletion. macOS only; no Windows compatibility claim.
