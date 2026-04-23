#!/bin/bash
# Wrapper globale per eseguire l'agent in Docker
echo ">>> [Docker Wrapper] Esecuzione in container con network=$CLAUDE_DOCKER_NETWORK image=$CLAUDE_DOCKER_IMAGE" >&2

exec docker run -i --rm \
  --network "$CLAUDE_DOCKER_NETWORK" \
  -e HOME=/root \
  -v "$PWD:/env" \
  -v "$HOME/.claude.json:/root/.claude.json:ro" \
  -v "$HOME/.claude:/root/.claude" \
  $CLAUDE_DOCKER_VOLUMES \
  -w /env \
  "$CLAUDE_DOCKER_IMAGE" npx -y @anthropic-ai/claude-code@latest "$@"
