# Agent V5 Kaggle - Source Files Configuration

## Overview

This Docker agent now uses the **original** `agent_v5` source files via a symbolic link, so any changes you make to the original files will be reflected in the Docker build.

## File Structure

```
/home/ubuntu/research/canada-research/
├── agent_v5/                              # ← ORIGINAL SOURCE (edit here!)
│   ├── agent.py
│   ├── tools/
│   └── ...
│
└── mle-bench/
    └── agents/
        └── agent_v5_kaggle/
            ├── agent_v5 → /home/.../agent_v5  # ← Symlink to original
            ├── Dockerfile
            └── runner.py
```

## How It Works

1. **Original source location:** `/home/ubuntu/research/canada-research/agent_v5/`
2. **Symlink in Docker context:** `agents/agent_v5_kaggle/agent_v5` → points to original
3. **When you build:** Docker follows the symlink and copies the original files
4. **Result:** Your changes to the original `agent_v5/` files are automatically included in the Docker image

## Making Changes

### To modify the agent logic:
```bash
# Edit the original files
vim /home/ubuntu/research/canada-research/agent_v5/agent.py
vim /home/ubuntu/research/canada-research/agent_v5/tools/[tool_file].py
```

### To rebuild with your changes:
```bash
cd /home/ubuntu/research/canada-research/mle-bench
./RUN_AGENT_V5_KAGGLE.sh  # This will rebuild the Docker image automatically
```

## Verifying the Setup

Check that the symlink is correct:
```bash
ls -la /home/ubuntu/research/canada-research/mle-bench/agents/agent_v5_kaggle/agent_v5
# Should show: agent_v5 -> /home/ubuntu/research/canada-research/agent_v5
```

## Important Notes

- **Always edit the original files** at `/home/ubuntu/research/canada-research/agent_v5/`
- **Don't edit** files inside `mle-bench/agents/agent_v5_kaggle/agent_v5/` (they're just a symlink)
- The Docker build automatically includes your latest changes
- Share changes by committing to the original `agent_v5/` directory
