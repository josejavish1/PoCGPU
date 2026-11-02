# 04. Despliegue del Enterprise AI Gateway

## 1. Misión de la Capa de Gateway en Arquitectura Tier-1
El Enterprise AI Gateway (LiteLLM Proxy / Envoy / Kong) desacopla a los clientes y aplicaciones de la infraestructura física de GPUs:
1. **Abstracción Total:** Las aplicaciones consumen nombres lógicos (`reasoning-model`, `light-model-fast`), sin conocer si detrás corre una GPU, dos GPUs con TP=2 o adaptadores LoRA.
2. **Gobernanza y Seguridad:** Gestión centralizada de API Keys virtuales por departamento, control de cuotas de presupuesto en dólares o tokens, y rate limiting (RPM / TPM).
3. **Resiliencia Operativa:** Manejo de reintentos automáticos, degradación elegante (fallbacks a modelos de menor tamaño en caso de congestión crítica) y timeouts diferenciados (ej. 300 segundos para cadenas de razonamiento frente a 30 segundos para respuestas rápidas).
4. **Cero Consumo de GPU:** El Gateway corre íntegramente sobre nodos CPU de bajo coste, con réplicas horizontales (HA) independientes del ciclo de vida de los motores de inferencia.

---

## 2. Despliegue del Gateway

Aplique el manifiesto ubicado en `manifests/04_gateway.yaml`:

```bash
kubectl apply -f /home/jsanchhi/PoCGPU/manifests/04_gateway.yaml
```

Verifique que las 2 réplicas del Gateway estén en ejecución:
```bash
kubectl get pods -l app=ai-gateway
```

Compruebe la conectividad interna del Service:
```bash
kubectl get svc enterprise-ai-gateway-svc
```

---

## 3. Pruebas de Consumo Funcional a través del Gateway

Desde cualquier Pod o máquina con acceso a la red del clúster (o mediante `kubectl port-forward`):

```bash
kubectl port-forward svc/enterprise-ai-gateway-svc 4000:80 &
```

### Test 1: Petición al Modelo de Razonamiento Profundo
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-tier1-master-governance-key-2026" \
  -d '{
    "model": "reasoning-model",
    "messages": [
      {
        "role": "user",
        "content": "¿Cómo diseñarías un sistema de almacenamiento distribuido tolerante a particiones de red? Razona paso a paso."
      }
    ],
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

### Test 2: Petición al Modelo Ligero Rápido
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-tier1-master-governance-key-2026" \
  -d '{
    "model": "light-model-fast",
    "messages": [
      {
        "role": "user",
        "content": "Clasifica el siguiente ticket: 'El usuario no puede resetear su contraseña'."
      }
    ],
    "temperature": 0.0,
    "max_tokens": 50
  }'
```

---

## 4. Métricas y Observabilidad (OTLP / Prometheus)

El Gateway expone métricas Prometheus en el endpoint `/metrics` en el puerto 4000:
- `litellm_proxy_total_requests`: Volumen total de solicitudes por modelo.
- `litellm_request_latency_seconds`: Latencia extremo a extremo desglosada por percentiles (P50, P90, P99).
- `litellm_spend_metric`: Consumo agregado de presupuesto y tokens por API Key.
