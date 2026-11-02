# 03. Despliegue del Motor vLLM con Tensor Parallelism (TP=2)

## 1. Justificación de los Parámetros de Inferencia de Producción

El manifiesto `manifests/03_vllm_service.yaml` implementa la directiva SOTA para consolidar múltiples modelos en un único proceso distribuido sobre las 2 GPUs:

1. `--tensor-parallel-size=2`:
   - Lanza 2 workers paralelos vinculados a `/dev/nvidia0` y `/dev/nvidia1`.
   - Divide los pesos de las matrices de proyección de atención y MLP a la mitad entre ambas tarjetas.
2. `--served-model-name=reasoning-deep`:
   - Registra un alias limpio para el modelo base (`reasoning-deep`), evitando tener que pasar la ruta física de disco `/models/...` en las llamadas API del Gateway.
3. `--gpu-memory-utilization=0.92`:
   - Instruye a vLLM a reservar el 92% de la memoria física de cada GPU.
   - El 8% restante se reserva para el contexto base de CUDA, buffers de activación dinámicos y margen para el compilador Torch.
   - **Mecanismo Dinámico:** Una vez cargados los pesos del modelo base (~19GB totales, ~9.5GB por GPU), el resto de la VRAM (más de 28GB en GPUs L4 o 140GB en A100) se asigna como **Pool de PagedAttention**.
4. `--enable-lora` y `--lora-modules`:
   - Permite que el mismo motor sirva el modelo pesado de razonamiento (`reasoning-deep`) y los dos modelos ligeros (`model-light-a` y `model-light-b`) de forma concurrente.
   - Si una petición solicita el modelo base, no aplica adaptadores. Si solicita un modelo ligero, vLLM inyecta los adaptadores LoRA en las multiplicaciones matriciales en tiempo de ejecución sin duplicar los 32B parámetros en VRAM.
5. `--max-model-len=8192`:
   - Fija la ventana de contexto máxima garantizada. Permite cadenas de razonamiento largas sin desbordar el presupuesto de bloques de memoria.
6. `volumeMounts: /dev/shm (sizeLimit: 16Gi)`:
   - **Requisito Crítico:** PyTorch Tensor Parallelism utiliza memoria compartida POSIX inter-proceso para coordinar los tensores entre GPUs. Si el tamaño de `/dev/shm` es el valor por defecto de Docker/K8s (64MB), el Pod colapsará instantáneamente con `Bus error (core dumped)` durante la inicialización de NCCL.

---

## 2. Ciclo de Vida del Pod y Probes

Durante el arranque de un modelo con Tensor Parallelism, vLLM realiza:
1. Lectura y carga de pesos desde disco a VRAM (~20-40 segundos).
2. Perfilado de memoria para calcular el tamaño exacto del pool de KV Cache (~10 segundos).
3. **Captura de Grafos CUDA (CUDA Graph Capture):** Precompila secuencias de ejecución en la GPU para tamaños de lote fijos (batch sizes 1, 2, 4, 8, etc.) para eliminar la sobrecarga de lanzamiento de kernels en CPU durante la generación de tokens (~60-120 segundos).

Por esta razón, se define un `startupProbe` con `failureThreshold: 30` y `periodSeconds: 10`, otorgando hasta 300 segundos para que el motor esté listo antes de que Kubernetes considere que el contenedor ha fallado.

---

## 3. Despliegue en el Clúster

Aplique el despliegue del motor y su Service de red interna:

```bash
kubectl apply -f /home/jsanchhi/PoCGPU/manifests/03_vllm_service.yaml
```

Supervise la inicialización y los logs de NCCL / vLLM:
```bash
kubectl logs -f deployment/vllm-inference-engine -c vllm-server
```

**Líneas de log esperadas que confirman el éxito:**
```text
INFO: Initializing an LLM engine (runner_type=ParallelGPUModelRunner) with config: model='/models/Qwen2.5-32B-Instruct-AWQ', tensor_parallel_size=2...
INFO: # GPU blocks: 18432, # CPU blocks: 2048
INFO: Capturing the model forward loop to craft a CUDA graph...
INFO: Graph capturing finished in 45 secs.
INFO: Route: /v1/chat/completions, Methods: POST
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Verifique el estado del servicio:
```bash
kubectl get svc vllm-engine-svc
```

---

## 4. Test Rápido de Inferencia Directa (Loopback en el Clúster)

Abra un túnel temporal o ejecute un `curl` desde un Pod dentro del clúster:

```bash
kubectl run curl-test --rm -it --image=curlimages/curl -- sh
```

Dentro del contenedor temporal:
```sh
# 1. Probar el Modelo de Razonamiento Profundo (Base)
curl -s http://vllm-engine-svc:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "reasoning-deep",
    "messages": [{"role": "user", "content": "Explica la segunda ley de la termodinámica en una frase."}],
    "max_tokens": 100
  }'

# 2. Probar el Modelo Ligero A (Vía Adaptador LoRA)
curl -s http://vllm-engine-svc:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-light-a",
    "messages": [{"role": "user", "content": "Resume este texto: Servidores de alta disponibilidad."}],
    "max_tokens": 50
  }'
```
