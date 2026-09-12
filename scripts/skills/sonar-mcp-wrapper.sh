#!/bin/bash
# Runs the SonarQube MCP Docker container with --add-host so the container
# can resolve shared.sonarqube.test via host-gateway (k3d ingress on the host).
# sonar run mcp has no network flags; this wrapper replicates its Docker call.

TOKEN=$(security find-generic-password -s "sonarqube-cli" -a "shared.sonarqube.test" -w 2>/dev/null)
if [ -z "$TOKEN" ]; then
  echo "sonar-mcp-wrapper: could not read SonarQube token from keychain. Run 'sonar auth login' first." >&2
  exit 1
fi

exec docker run --rm -i \
  --add-host="shared.sonarqube.test:host-gateway" \
  -e "SONARQUBE_TOKEN=$TOKEN" \
  -e "SONARQUBE_URL=http://shared.sonarqube.test/" \
  -e "SONARQUBE_TOOLSETS=analysis,issues,projects,quality-gates,rules,duplications,measures,security-hotspots,dependency-risks,coverage" \
  -e "SONARQUBE_MCP_IN_CONTAINER=true" \
  sonarsource/sonarqube-mcp:latest
