# Policy format v1

Phase 4 migration: `ReleaseRule.max_releases` is an integer 1–128, default **1**.
This deliberately tightens old grants that omitted a repeat budget. Each exact
source/destination counter is broker-wide and survives new sessions/policy reloads;
attempts reserve before source access, including failure/unknown I/O. Raising the
budget is an explicit operator decision. Restart resets memory-only counters.
Cardinality, validity and timing are still observable; no differential privacy is
claimed. The final-answer gate also withholds arbitrary model prose after a count.

## Phase 3 opt-in release

The authenticated operator console/API validates complete policy JSON with an
expected digest. Agent credentials cannot edit it. Duplicate JSON keys, unknown
fields and duplicate identifiers are rejected. Default release_rules is empty.

Add this field to a complete policy only for a deliberately approved workflow:

```json
"release_rules": [{
  "id": "approved-count", "source": "sensitive/records.json",
  "destination": "http://127.0.0.1:8766/collect",
  "projector": "record_count_v1", "max_records": 8
}]
```

The policy must also ALLOW read_file on that source and post_message to that
destination. A matching read/send DENY or approval requirement prevents release.
A broad ordinary Rule for export_count is rejected. The source must be classified
sensitive. The caller supplies only path and url, never a body or formatter.

Trusted code parses at most 32 KiB of exactly this JSON structure:
`{"schema":"zyntrava.records.v1","records":[{"id":"a","value":"dummy"}]}`.
There is no extra key, duplicate key, non-finite constant or type coercion. At most
128 records; IDs are lower-case ASCII/digit/hyphen, 1–32 characters; values at most
512 characters. max_records is 0–128. The entire outgoing body is constructed by
trusted code: `{"record_count":1,"schema":"zyntrava.record-count.v1"}`.
Raw source values do not enter model context through this tool. Cardinality is
deliberately disclosed; validity, timing and repeated-use channels remain. Ordinary
sinks stay denied after release, including authorized attempts that fail parsing.
This is not general-purpose safe summarization or differential privacy.

## Ordinary permissions

The generated `.state/policy.json` is the executable example. Edit it offline as an
operator and restart the broker, or use the authenticated control API. JSON parsing is
strict, unknown fields and duplicate rule IDs are rejected. Rules are immutable
typed objects. Every decision records a SHA-256 policy digest.

```json
{
  "version": 1,
  "name": "local-lab-v1",
  "sensitive_roots": ["sensitive"],
  "rules": [
    {"id": "read-docs", "tool": "read_file", "effect": "allow", "path_prefix": "public"},
    {"id": "deny-private", "tool": "read_file", "effect": "deny", "path_prefix": "private"},
    {"id": "review-reports", "tool": "write_file", "effect": "approve", "path_prefix": "reports"},
    {"id": "local-receiver", "tool": "post_message", "effect": "allow", "destination": "http://127.0.0.1:8766/collect"}
  ]
}
```

Matching uses tool identity and a path-segment prefix or exact destination. Deny
takes precedence over approve, then allow. No matching rule means deny. A network
rule cannot specify a path prefix; a file rule cannot specify a destination.
There are no wildcard tools, domain suffix rules, regular expression permissions,
shell commands or model-evaluated policy clauses.

File paths are portable relative POSIX paths, currently with ASCII components.
Absolute paths, traversal, backslashes, colons, special device names, empty
segments, trailing periods/spaces and linked/reparse components are refused.
Prefix matching uses case-folded segments on every OS (`public` does not match
`publicity`). Existing parents are required. Writes create exclusively and never
overwrite. Reads are UTF-8 with a 32 KiB output cap; sink fields allow 16,384
characters each. See the threat model for filesystem race assumptions.

Network execution supports only canonical `http://127.0.0.1:<port>/<path>` endpoints
on ports 1024–65535, exactly named in policy. No credentials, query, fragment,
percent-encoded path, DNS name, redirects, arbitrary headers or proxy inheritance.
This narrow lab implementation is not a general-purpose HTTP firewall.

Literal DLP denies recognizable credential-shaped sink contents regardless of
destination. Full mode additionally blocks every sink after a sensitive-root read
or recognized secret source. An approval cannot declassify or override these
denials. Heuristics observe suspicious instructions without automatically blocking
an otherwise authorized operation. Default policy sensitive reads exist only to
exercise the synthetic lab experiment.
