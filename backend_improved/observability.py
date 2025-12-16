# OBSERVABILITY

# --------------- PHOENIX ------------------------
import phoenix as px
from phoenix.otel import register
from opentelemetry.trace import Status, StatusCode
phoenix_project_name = "manrique-rag"

# self-hosted
# endpoint="http://127.0.0.1:6006/v1/traces"
# tracer_provider_phoenix = register(project_name=phoenix_project_name, endpoint = endpoint)

# arize
endpoint="https://app.phoenix.arize.com/s/lveyssier/v1/traces"
tracer_provider_phoenix = register(
  project_name=phoenix_project_name,
  endpoint=endpoint,
  auto_instrument=True
)