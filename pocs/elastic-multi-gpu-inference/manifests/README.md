# Deployment manifests

The manifests require a Kubernetes Secret named `ai-platform-secrets` in the target namespace. Provision it through the organization's approved secret manager before applying the workloads. The repository never stores secret values.

The Secret must expose these keys:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `LITELLM_MASTER_KEY`
- `WEBUI_SECRET_KEY`

The gateway also expects the existing `gemini-api-secret` Secret with a `GEMINI_API_KEY` key when cloud overflow is enabled. Deployment automation may replace these names through an environment-specific rendering layer.
