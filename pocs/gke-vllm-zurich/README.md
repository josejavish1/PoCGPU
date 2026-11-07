# GKE vLLM Distributed Inference PoC (Zurich)

This directory contains the declarative manifests and operational runbooks for the multi-GPU inference PoC deployed on Google Kubernetes Engine (GKE) in Zurich (`europe-west6-b`).

## Architecture Topology

- **CPU Node Pool (`default-pool`):** 1x `e2-standard-2` On-Demand node running LiteLLM Gateway, PostgreSQL, OpenWebUI, Prometheus, and Grafana.
- **GPU Node Pool (`gpu-pool`):** 2x `g2-standard-24` Spot nodes with 2x NVIDIA L4 GPUs each (4x L4 GPUs = 96 GB VRAM combined), executing vLLM with Tensor Parallelism (TP=2) and dynamic Multi-LoRA serving.

## Directory Structure

```text
pocs/gke-vllm-zurich/
├── manifests/                    # Declarative Kubernetes manifests
│   ├── 01_gpu_audit.yaml        # GPU interconnect audit and bandwidth test
│   ├── 02_storage.yaml          # Base PVC and Safetensors preload job
│   ├── 02_storage_zurich.yaml   # Persistent disk binding (Node 1)
│   ├── 02_storage_replica2.yaml # Persistent disk binding (Node 2)
│   ├── 03_vllm_service.yaml     # vLLM Server 1 Deployment (TP=2, 2x L4) + ClusterIP
│   ├── 03_vllm_replica2.yaml    # vLLM Server 2 Deployment (TP=2, 2x L4) + ClusterIP
│   ├── 04_gateway.yaml          # LiteLLM Gateway + PostgreSQL + Router ConfigMap
│   ├── 05_linux_client.yaml     # In-cluster Linux benchmark client pod
│   ├── 06_openwebui.yaml        # OpenWebUI chat frontend
│   └── README.md                # Manifests index
├── runbooks/                    # Operational runbooks (00 through 08)
│   ├── 00_ARQUITECTURA_Y_PRINCIPIOS.md
│   ├── 01_VALIDACION_HARDWARE_Y_FABRIC.md
│   ├── 02_STORAGE_Y_PESOS.md
│   ├── 03_DESPLIEGUE_MOTOR_VLLM_TP2.md
│   ├── 04_ENTERPRISE_AI_GATEWAY.md
│   ├── 05_PRUEBAS_DE_CARGA_Y_BENCHMARK.md
│   ├── 06_GUIA_PRACTICA_POC_SATURACION.md
│   ├── 07_VARIANTE_MINIMO_COSTE_SPOT_MISTRAL.md
│   └── 08_ESTADO_ZURICH_Y_OPERACIONES.md
└── scripts/                     # Cluster load testing, benchmark, and probes
    ├── benchmark.py             # Mixed concurrency benchmark (TTFT, TPOT)
    ├── saturation_probe.py      # KV Cache extreme saturation tester
    ├── seed_enterprise_demo.py  # Seed departments, budgets, and keys
    └── ...                      # Observability and simulator scripts
```

## Fast Operations

### Reactivation
```bash
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=default-pool --num-nodes=1 --zone=europe-west6-b --quiet
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=gpu-pool --num-nodes=2 --zone=europe-west6-b --quiet
```

### Hibernation (Zero Compute Cost)
```bash
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=gpu-pool --num-nodes=0 --zone=europe-west6-b --quiet
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=default-pool --num-nodes=0 --zone=europe-west6-b --quiet
```

### Service Tunnels
```bash
kubectl port-forward --address 0.0.0.0 svc/open-webui-svc 8000:80 &
kubectl port-forward --address 0.0.0.0 svc/enterprise-ai-gateway-svc 8080:80 &
kubectl port-forward --address 0.0.0.0 svc/grafana-service 8082:3000 &
```
