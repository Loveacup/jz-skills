# Privacy Review for Crossing Artifacts

Load this reference only when files, generated output, or repository history will cross a trust boundary, such as a public release, a transfer to another organization, or a runtime-to-source import. It supplements the active import or release workflow; it does not authorize the transfer, publication, history rewrite, credential action, or deployment.

## Establish the review set

Derive the review set from the exact export, staging set, manifest, archive, or named transfer target. Cover every artifact that the operation intends to expose, including generated or bundled outputs and content reached indirectly through links or packaging. Typical forms include source and reference text, scripts, templates, examples, fixtures, configuration, manifests, catalogs, release metadata, logs or transcripts, evidence files, images and document metadata, archives, and symlink targets.

Do not treat that list as a fixed checklist. The set is complete only when every intended output byte can be traced to a reviewed input or reviewed transformation. Reject an unresolved symlink, generated file, nested archive, or other indirection rather than assuming its contents are safe. Do not scan unrelated private directories merely because they are nearby.

For repository publication, inspect history only when the operation newly exposes it. Review commits, tags, branches, and objects newly reachable from the exact ref being published, compared with what the destination already exposes. A new standalone artifact does not justify scanning all local refs, and a narrow push must not silently become a whole-history audit.

## Classify findings by consequence

Review automated matches and semantic context for these risk classes:

- **Credentials and authority:** private keys, passwords, access or refresh tokens, cookies, signed URLs, connection strings, webhook secrets, recovery material, or live secret values in assignments.
- **Personal and private content:** personal contact details, private names or identifiers, user-specific home or vault paths, private notes, raw conversations, and embedded document or image metadata.
- **Internal environment:** private hosts and addresses, account, tenant, device, session, job, instance, profile, or repository identifiers; internal topology, ports, service names, and operational evidence that would reveal private infrastructure.
- **Unapproved payloads:** proprietary, licensed, customer, third-party, or generated material whose publication rights or intended audience are not established.
- **Operational residue:** caches, state, lock files, debug dumps, temporary outputs, backups, and evidence packages that were never intended to be part of the public artifact.
- **Benign lookalikes:** documentation placeholders, reserved example addresses, public citations, hashes, versions, and prose that names a secret type without containing a secret value.

Risk follows what the value grants or reveals, not the pattern name alone. A prompt saying “do not expose credentials” is guidance, not a security boundary; use controlled artifact selection, scanners, parsers, and release controls for enforceable protection.

## Scan without blind spots

Use detectors appropriate to the formats and expected risks, then semantically review every match. Search both obvious values and structural clues such as credential-bearing filenames, assignments, authorization headers, user-specific paths, identifiers, metadata fields, and encoded or packaged content.

Record benign matches in an exact allowlist containing the artifact path, exact literal or stable fingerprint, reason it is safe, and the evidence or reviewer responsible for that decision. Never exclude an entire directory, extension, template tree, or reference tree to silence matches. Invalidate or re-review an allowlist entry when its file or matched value changes.

Automated silence is not a privacy verdict. Inspect context for values scanners cannot recognize, and confirm that the artifact set itself did not omit a generated or staged output.

## Transform by artifact type

Prefer removing material that is unnecessary for the public behavior. When a value is needed as an example, replace it with a format-valid reserved value and preserve the surrounding contract:

- keep shell quoting, variable names, argument boundaries, and expansion semantics valid;
- keep JSON, YAML, TOML, and frontmatter parseable and preserve their value types;
- use explicit portable paths where tilde expansion would not occur;
- preserve URLs, identifiers, and examples only in forms that cannot grant authority or identify the private environment;
- rebuild archives and generated outputs from sanitized inputs rather than patching opaque bytes;
- remove private image or document metadata and inspect visible content as well as extracted text.

Do not insert prose placeholders into executable syntax or replace values so broadly that the example changes meaning. After a syntax-sensitive edit, run the relevant parser or syntax check and repeat the changed-path behavior or generation scenario. Re-scan the final crossing artifact, not only its source. A clean scan does not prove valid syntax or preserved behavior.

## Blocking and remediation boundaries

A live or plausibly live credential in the crossing set blocks publication until it is removed and the final artifact is clean. If the credential has already been exposed, preserve evidence without reproducing the value and report the exposure. Revocation or rotation, remote deletion, repository history repair, force updates, and consumer migration are separate consequential actions; perform each only with authorization for its named target.

Missing publication rights, unresolved private payloads, opaque artifacts, or an unavailable required scanner/parser produce `BLOCKED` for the affected transfer. Do not claim privacy from a prompt, a partial scan, a directory exclusion, or a sanitized source whose packaged output was not reviewed.

Return the reviewed artifact set, risk findings and exact dispositions, allowlisted false positives, transformations performed, syntax or behavior evidence, history scope if applicable, and any blocked remediation or authorization boundary. Release state and named-target authorization remain owned by the [release workflow](release.md).