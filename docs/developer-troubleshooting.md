# Developer troubleshooting

| Symptom | Action |
| --- | --- |
| Wrong Python/venv unavailable | Use approved Python 3.13 and its matching venv support. Verify the actual environment interpreter. |
| Optional agent import error | Install requirements-preview.txt using the same Python, then source with --no-deps. |
| Hash mismatch | Stop and verify file/revision/package origin. Do not remove hash checking. |
| Build backend unavailable | Source installation uses pinned Hatchling through normal build isolation; check approved package connectivity. |
| Host blocks executable | Use an approved full interpreter/standard venv. Do not disable application control. |
| Output already exists | Preserve old evidence and choose a NEW artifacts/ path. |
| Missing/invalid model | Install pinned assets on Windows, verify hashes and available RAM/VRAM/disk. Never substitute unverified weights. |
| Linux neural run fails | The current local launcher targets Windows Vulkan. Use scripted/core checks; native Linux inference is unverified. |
| WSL installation on /mnt/c is very slow | Use a separate native-Linux source/venv. The shared-mount attempt timed out; native clean installation passed. Do not share Windows/Linux venvs. |
| Port busy | Stop only an owned prior server. Keep fixed ports for matched evaluations or document the deviation. |
| No CUDA | The pinned runtime uses Vulkan; CUDA is not its prerequisite. |
| Stops after denial | Known utility failure. Preserve evidence; do not broaden policy or enable failed recovery candidates. |
| Model says it posted, no receipt | Task incomplete. Prose is not execution. |
| Attack did not activate | Report nonactivation, not a successful block. |
| Duplicate reports | Record duplicates; default SDK has no general exactly-once guarantee. Never retry uncertain effects. |
| Dashboard disconnected | Correct for a separate SDK broker; opening the UI does not connect an agent. |
| UI assets missing | Build dashboard with Node, then serve from this source directory. SDK exercise needs no frontend. |
| Audit failure | Stop and preserve it. Do not disable audit requirements. |

Use the installation-feedback template in the exercise. Include exact commands,
OS/Python/package versions and redacted errors; omit environment dumps, tokens,
home-directory listings and real-data transcripts. Vulnerabilities use SECURITY.md.
