# 07. Variante de Mínimo Coste: VMs Spot, GPUs L4 y Modelos Públicos Mistral

## 1. Validación de Licencia: ¿Es Mistral Público?
**Sí.** El modelo `mistralai/Mistral-7B-Instruct-v0.3` es de código abierto bajo **Licencia Apache 2.0**:
- Permite uso comercial, modificación, redistribución y auto-alojamiento privado sin pagar royalties ni suscripciones.
- No requiere aprobación previa ni tokens de pago en Hugging Face (pesos de acceso público inmediato).

---

## 2. Presupuesto Económico: Despliegue en GCP con Instancias Spot

En Google Cloud, el uso de **Spot VMs** (capacidad sobrante de Google con hasta un 70% de descuento) reduce el coste de la PoC a céntimos:

| Componente | Tipo de Recurso | Modo de Facturación | Coste por Hora (Aprox.) | Coste PoC (2 Horas) |
| :--- | :--- | :--- | :--- | :--- |
| **Computación + 2 GPUs** | Instancia `g2-standard-24` (2x NVIDIA L4 24GB) | **GCP Spot VM** | ~$0.78 / hora | **~$1.56 USD** |
| **Almacenamiento** | Persistent Disk SSD 150 GiB (`pd-ssd`) | Estándar por hora | ~$0.04 / hora | **~$0.08 USD** |
| **Plano de Control GKE** | GKE Standard Cluster (1 clúster libre) | Estándar | ~$0.10 / hora | **~$0.20 USD** |
| **TOTAL ESTIMADO PoC** | Infraestructura completa operativa | **Spot** | **~$0.92 / hora** | **< $1.90 USD** |

*Alternativa ultra-económica:* Usar 2x NVIDIA T4 (`n1-standard-8` + 2 T4 Spot) por **~$0.40 / hora**, pero las L4 son recomendadas por soportar kernels modernos de vLLM y mayor velocidad de cálculo.

---

## 3. Comando de Creación del Node Pool Spot en GKE

Ejecute la creación del pool de nodos con el flag `--spot`:

```bash
gcloud container node-pools create gpu-spot-pool \
  --cluster=ai-poc-cluster \
  --region=us-central1 \
  --machine-type=g2-standard-24 \
  --accelerator=type=nvidia-l4,count=2,gpu-driver-version=default \
  --spot \
  --num-nodes=1 \
  --node-locations=us-central1-a
```

---

## 4. Adaptación del Manifiesto vLLM para Mistral-7B

Al usar Mistral-7B sobre 2 GPUs L4 (48 GB totales de VRAM), los pesos ocupan solo ~14 GB (~7 GB por GPU).

### Cómo Forzar la Saturación Rápida para la Prueba:
Para no necesitar 100 clientes enviando peticiones durante horas para ver cómo se comporta la saturación, ajustamos el flag `--gpu-memory-utilization` a un valor bajo (ej. `0.40`). Esto limita artificialmente el espacio de KV Cache, provocando que **con solo 6 a 8 usuarios simultáneos el sistema entre en saturación, active la cola de espera y demuestre la resiliencia**:

```yaml
# Fragmento para manifests/03_vllm_service.yaml adaptado a Mistral-7B Spot
containers:
- name: vllm-server
  image: vllm/vllm-openai:v0.6.3
  args:
  - "--model=mistralai/Mistral-7B-Instruct-v0.3"
  - "--served-model-name=reasoning-deep"
  - "--tensor-parallel-size=2"
  - "--gpu-memory-utilization=0.45" # Limita la VRAM a ~10GB para saturar con poco tráfico
  - "--max-model-len=4096"
  - "--port=8000"
```

---

## 5. Protocolo de Pruebas de Mínimo Coste

1. **Levantar:** Aplicar los manifiestos (`kubectl apply -f manifests/`).
2. **Medir y Saturar:** Ejecutar `scripts/benchmark.py --concurrency 8 --rounds 3`.
3. **Comprobar:** Revisar la cola en el Dashboard Web de LiteLLM (`http://localhost:4000/ui`).
4. **Destruir Inmediatamente:**
   ```bash
   gcloud container clusters delete ai-poc-cluster --region=us-central1 --quiet
   ```
   *Destruir el clúster al terminar garantiza que el gasto total de la prueba no supere los 2 dólares.*
