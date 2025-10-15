#!/bin/bash
# Quick setup script for Git LFS in your terminal session

export PATH=$HOME/.local/bin:$PATH
echo "✅ Git LFS is now available in this terminal session!"
echo "   Version: $(git lfs version 2>/dev/null || echo 'Git LFS not found')"


