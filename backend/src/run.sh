#!/bin/bash
# Lambda handler entry point. Lambda Web Adapter (/opt/bootstrap) runs this script,
# waits for GET /healthz, then forwards each API Gateway request to the server.
exec python3 -m proxy.server
