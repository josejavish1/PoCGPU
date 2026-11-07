# Entorno Declarativo de PoCs Cloud (Inference Infrastructure)

Este directorio alberga los entornos de despliegue declarativo (Kubernetes, Helm, scripts de nube) para validar arquitecturas de inferencia en aceleradores físicos.

Cada subdirectorio representa una PoC completamente aislada y autónoma con sus propios manifiestos, topología y runbooks operativos.

## PoCs Disponibles

- **`elastic-multi-gpu-inference/`:** Clúster GKE en Zúrich (`europe-west6-b`) con 4x NVIDIA L4 GPUs, vLLM con Tensor Parallelism (TP=2), Multi-LoRA dinámico, LiteLLM Enterprise Gateway en CPU y frontend OpenWebUI.

## Convención para Nuevas PoCs

Para añadir una nueva PoC (ejemplo: `pocs/aws-bedrock-private/` o `pocs/gke-h100-megatron/`):
1. Crear un subdirectorio aislado bajo `pocs/<nombre-de-la-poc>/`.
2. Incluir `manifests/` con la configuración declarativa de infraestructura.
3. Incluir `runbooks/` con los procedimientos operativos de verificación y benchmarks.
4. Incluir un `README.md` con la topología y comandos de ciclo de vida (arranque, parada/hibernación).
5. Las PoCs no deben tener dependencias de código con el motor de software de las calculadoras.
