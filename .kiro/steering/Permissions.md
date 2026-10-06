# AWS Permissions

This environment has limited AWS permissions. When creating solutions, only use actions that are permitted.

## Region

All AWS operations must target **us-east-1**.

## Allowed Actions

| Action | Service |
|--------|---------|
| `Converse` | bedrock-runtime |
| `ConverseStream` | bedrock-runtime |
| `InvokeModel` | bedrock-runtime |
| `InvokeModelWithResponseStream` | bedrock-runtime |

## Denied Actions

| Action | Service |
|--------|---------|
| `ListFoundationModels` | bedrock |
| `GetFoundationModel` | bedrock |
| `ListGuardrails` | bedrock |
| `GetGuardrail` | bedrock |

## Rules

- Do not use Bedrock control-plane actions (bedrock:*). They are denied.
- Only bedrock-runtime actions are permitted.
- The available model is `amazon.nova-lite-v1:0`.
- The Strands Agents framework works because it only uses `bedrock-runtime:Converse` / `ConverseStream`.
- Do not attempt to list, describe, or manage foundation models or guardrails via the API.
- IAM access is not available; do not attempt IAM operations.
