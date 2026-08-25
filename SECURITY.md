# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :x:                |
| < 1.1   | :x:                |

Current release: `1.2.0`.

## Trust Model

Siss is a local CLI tool. The caller is trusted with filesystem access, and
the tool operates entirely within the current working directory. Output paths
are normalized with `os.path.realpath()` and rejected if they escape the
working directory.

Subprocess calls to `ffmpeg` and `ffprobe` use list arguments (no
`shell=True`), preventing shell injection. The binary paths are resolved from
the `SISS_FFMPEG` and `SISS_FFPROBE` environment variables when set, falling
back to `shutil.which()`. In environments where the process environment is
not trusted (e.g., CI runners executing untrusted code), those variables
should be cleared before invoking Siss.

The `-vv` (DEBUG) log level outputs full exception tracebacks, which may
include local filesystem paths and module names. In automated pipelines,
prefer `-v` (INFO) or the default WARNING level to avoid leaking internal
paths into log aggregation.

## Reporting a Vulnerability

Siss is published on PyPI and consumed as a dependency. If you discover a
security vulnerability, please report it privately rather than opening a
public issue.

Use GitHub's **Report a vulnerability** button on the
[Security](https://github.com/MichailSemoglou/siss/security) tab. That opens a
private draft advisory visible only to the maintainer and, after acceptance,
to collaborators the maintainer adds.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce, including a minimal input file or command if applicable.
- The affected version or commit range.
- Any suggested fixes or mitigations.

The maintainer acknowledges reports within 72 hours and aims to publish a fix
within 30 days. After the fix is released, the reporter will be credited in
the advisory unless they request otherwise.
