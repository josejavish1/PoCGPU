# Full Taxonomy of vLLM v0.6.3 Engine Parameters (113 Parameters)

This document provides an exhaustive, production-grade audit of all 113 command-line parameters in vLLM v0.6.3.
It categorizes each parameter by operational domain and flags its direct impact on GPU VRAM Sizing, Concurrency/Throughput, and Semantic Quality.

## Executive Breakdown by Architectural Tier

| Architectural Tier | Count | Impact on Sizing & FinOps | Impact on Latency / Throughput | Impact on Semantic Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Tier 1: Core Performance, KV-Cache & Sizing** | 13 | **CRITICAL** (Governs number of GPUs needed) | **CRITICAL** (2x-4x throughput variance) | High (Only if Quantization/Context limit applied) |
| **Tier 2: Multi-LoRA & Dynamic Specialization** | 10 | Medium (VRAM budget for adapter weights) | Medium (LoRA kernel overhead) | High (Determines adapter rank & task accuracy) |
| **Tier 3: Distributed Fabric & GPU Parallelism** | 6 | High (Determines TP/PP split across cards) | High (Inter-GPU All-Reduce communication) | Zero (Math is strictly identical) |
| **Tier 4: Speculative & Draft Decoding** | 7 | Low (Memory for small draft model) | High (1.5x-2x faster decode on small batches) | Zero (Draft tokens are strictly verified) |
| **Tier 5: Model Artifact & Tokenizer Loading** | 23 | Zero (One-time startup operation) | Zero (Static load time only) | Zero (Standard huggingface weight parser) |
| **Tier 6: Web Server, API & Networking Plumbing** | 54 | Zero (Standard Uvicorn/FastAPI HTTP layer) | Low (HTTP connection pooling/framing) | Zero (Pass-through request gateway) |
| **TOTAL** | **113** | | | |

---

## Tier 1: The 13 Core Performance, Sizing & Quality Parameters

These 13 parameters directly feed the mathematical equations in `calculators/sizing` and `calculators/chargeback`:

| Parameter Flag | Default | Domain | Impact on Sizing Calculator ($N_{gpus}$) | Impact on User Latency (TTFT / TPOT) | Impact on Quality |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `--kv-cache-dtype` | `auto` | Memory | **Halves VRAM needed per user** (FP8 vs FP16). | Doubles concurrent capacity before queuing. | <0.05% perplexity drift. |
| `--gpu-memory-utilization` | `0.9` | Memory | **Sets total VRAM pool** for KV cache. | Prevents OOM crashes under sudden load. | Zero. |
| `--enable-chunked-prefill` | `None` | Scheduling | Reduces peak VRAM spikes during prefill. | **Eliminates Head-of-Line blocking** (-50% P99 TTFT). | Zero. |
| `--enable-prefix-caching` | `False` | Attention | Allows multi-tenant prompt deduplication. | **10x faster TTFT** (<30ms) on shared contexts. | Zero. |
| `--max-num-batched-tokens` | `None` | Compute | Governs iteration chunk budget (e.g. 2048). | Satures Tensor Core compute pipelines. | Zero. |
| `--block-size` | `16` | Memory | Page block size in VRAM (16 vs 32). | Memory bus coalescing on L4/A100 GPUs. | Zero. |
| `--max-num-seqs` | `256` | Scheduling | Max concurrent active streams per loop. | Caps concurrency to preserve per-user fluidity. | Zero. |
| `--max-model-len` | `None` | Context | **Caps maximum context window** per stream. | Prevents single user from monopolizing VRAM. | Clips prompts > max len. |
| `--quantization` | `None` | Weights | **Halves/quarters model weight VRAM** (AWQ/FP8). | Accelerates memory bandwidth bound decode. | 1-3% loss in accuracy. |
| `--dtype` | `auto` | Weights | Precision format (FP16, BF16, FP8). | Baseline memory and tensor core execution format. | Zero. |
| `--enforce-eager` | `False` | Kernel | Disables CUDA graphs if True. | True adds 20-30% CPU dispatch overhead to TPOT. | Zero. |
| `--swap-space` | `4` | Memory | GiB in host RAM for KV cache offloading. | Emergency buffer to prevent OOM termination. | Zero. |
| `--fully-sharded-loras` | `False` | LoRA | Shards adapter computation across tensor parallel GPUs. | Saves 50% adapter VRAM in multi-GPU nodes. | Zero. |

---

## Complete Exhaustive Catalog of All 113 Parameters

| # | Parameter Flag | Default | Description |
| :---: | :--- | :---: | :--- |
| 1 | `--host` | `None` | host name |
| 2 | `--port` | `8000` | port number |
| 3 | `--uvicorn-log-level` | `info` | log level for uvicorn |
| 4 | `--allow-credentials` | `False` | allow credentials |
| 5 | `--allowed-origins` | `['*']` | allowed origins |
| 6 | `--allowed-methods` | `['*']` | allowed methods |
| 7 | `--allowed-headers` | `['*']` | allowed headers |
| 8 | `--api-key` | `None` | If provided, the server will require this key to be presented in the header. |
| 9 | `--lora-modules` | `None` | LoRA module configurations in either 'name=path' formator JSON format. Example (old format): 'name=path' Example (new format): '{"name": "name", "local_path": "path", "base_model_name": "id"}' |
| 10 | `--prompt-adapters` | `None` | Prompt adapter configurations in the format name=path. Multiple adapters can be specified. |
| 11 | `--chat-template` | `None` | The file path to the chat template, or the template in single-line form for the specified model |
| 12 | `--response-role` | `assistant` | The role name to return if `request.add_generation_prompt=true`. |
| 13 | `--ssl-keyfile` | `None` | The file path to the SSL key file |
| 14 | `--ssl-certfile` | `None` | The file path to the SSL cert file |
| 15 | `--ssl-ca-certs` | `None` | The CA certificates file |
| 16 | `--ssl-cert-reqs` | `0` | Whether client certificate is required (see stdlib ssl module's) |
| 17 | `--root-path` | `None` | FastAPI root_path when app is behind a path based routing proxy |
| 18 | `--middleware` | `[]` | Additional ASGI middleware to apply to the app. We accept multiple --middleware arguments. The value should be an import path. If a function is provided, vLLM will add it to the server using @app.middleware('http'). If a class is provided, vLLM will add it to the server using app.add_middleware(). |
| 19 | `--return-tokens-as-token-ids` | `False` | When --max-logprobs is specified, represents single tokens as strings of the form 'token_id:{token_id}' so that tokens that are not JSON-encodable can be identified. |
| 20 | `--disable-frontend-multiprocessing` | `False` | If specified, will run the OpenAI frontend server in the same process as the model serving engine. |
| 21 | `--enable-auto-tool-choice` | `False` | Enable auto tool choice for supported models. Use --tool-call-parserto specify which parser to use |
| 22 | `--tool-call-parser` | `None` | Select the tool call parser depending on the model that you're using. This is used to parse the model-generated tool call into OpenAI API format. Required for --enable-auto-tool-choice. |
| 23 | `--tool-parser-plugin` | `` | Special the tool parser plugin write to parse the model-generated tool into OpenAI API format, the name register in this plugin can be used in --tool-call-parser. |
| 24 | `--model` | `facebook/opt-125m` | Name or path of the huggingface model to use. |
| 25 | `--tokenizer` | `None` | Name or path of the huggingface tokenizer to use. If unspecified, model name or path will be used. |
| 26 | `--skip-tokenizer-init` | `False` | Skip initialization of tokenizer and detokenizer |
| 27 | `--revision` | `None` | The specific model version to use. It can be a branch name, a tag name, or a commit id. If unspecified, will use the default version. |
| 28 | `--code-revision` | `None` | The specific revision to use for the model code on Hugging Face Hub. It can be a branch name, a tag name, or a commit id. If unspecified, will use the default version. |
| 29 | `--tokenizer-revision` | `None` | Revision of the huggingface tokenizer to use. It can be a branch name, a tag name, or a commit id. If unspecified, will use the default version. |
| 30 | `--tokenizer-mode` | `auto` | The tokenizer mode.  * "auto" will use the fast tokenizer if available. * "slow" will always use the slow tokenizer.  * "mistral" will always use the `mistral_common` tokenizer. |
| 31 | `--trust-remote-code` | `False` | Trust remote code from huggingface. |
| 32 | `--download-dir` | `None` | Directory to download and load the weights, default to the default cache dir of huggingface. |
| 33 | `--load-format` | `auto` | The format of the model weights to load.  * "auto" will try to load the weights in the safetensors format and fall back to the pytorch bin format if safetensors format is not available. * "pt" will load the weights in the pytorch bin format. * "safetensors" will load the weights in the safetensors format. * "npcache" will load the weights in pytorch format and store a numpy cache to speed up the loading. * "dummy" will initialize the weights with random values, which is mainly for profiling. * "tensorizer" will load the weights using tensorizer from CoreWeave. See the Tensorize vLLM Model script in the Examples section for more information. * "bitsandbytes" will load the weights using bitsandbytes quantization. |
| 34 | `--config-format` | `auto` | The format of the model config to load.  * "auto" will try to load the config in hf format if available else it will try to load in mistral format |
| 35 | `--dtype` | `auto` | Data type for model weights and activations.  * "auto" will use FP16 precision for FP32 and FP16 models, and BF16 precision for BF16 models. * "half" for FP16. Recommended for AWQ quantization. * "float16" is the same as "half". * "bfloat16" for a balance between precision and range. * "float" is shorthand for FP32 precision. * "float32" for FP32 precision. |
| 36 | `--kv-cache-dtype` | `auto` | Data type for kv cache storage. If "auto", will use model data type. CUDA 11.8+ supports fp8 (=fp8_e4m3) and fp8_e5m2. ROCm (AMD GPU) supports fp8 (=fp8_e4m3) |
| 37 | `--quantization-param-path` | `None` | Path to the JSON file containing the KV cache scaling factors. This should generally be supplied, when KV cache dtype is FP8. Otherwise, KV cache scaling factors default to 1.0, which may cause accuracy issues. FP8_E5M2 (without scaling) is only supported on cuda versiongreater than 11.8. On ROCm (AMD GPU), FP8_E4M3 is instead supported for common inference criteria. |
| 38 | `--max-model-len` | `None` | Model context length. If unspecified, will be automatically derived from the model config. |
| 39 | `--guided-decoding-backend` | `outlines` | Which engine will be used for guided decoding (JSON schema / regex etc) by default. Currently support https://github.com/outlines-dev/outlines and https://github.com/noamgat/lm-format-enforcer. Can be overridden per request via guided_decoding_backend parameter. |
| 40 | `--distributed-executor-backend` | `None` | Backend to use for distributed serving. When more than 1 GPU is used, will be automatically set to "ray" if installed or "mp" (multiprocessing) otherwise. |
| 41 | `--worker-use-ray` | `False` | Deprecated, use --distributed-executor-backend=ray. |
| 42 | `--pipeline-parallel-size/-pp` | `1` | Number of pipeline stages. |
| 43 | `--tensor-parallel-size/-tp` | `1` | Number of tensor parallel replicas. |
| 44 | `--max-parallel-loading-workers` | `None` | Load model sequentially in multiple batches, to avoid RAM OOM when using tensor parallel and large models. |
| 45 | `--ray-workers-use-nsight` | `False` | If specified, use nsight to profile Ray workers. |
| 46 | `--block-size` | `16` | Token block size for contiguous chunks of tokens. This is ignored on neuron devices and set to max-model-len |
| 47 | `--enable-prefix-caching` | `False` | Enables automatic prefix caching. |
| 48 | `--disable-sliding-window` | `False` | Disables sliding window, capping to sliding window size |
| 49 | `--use-v2-block-manager` | `True` | Use BlockSpaceMangerV2. By default this is set to True. Set to False to use BlockSpaceManagerV1 |
| 50 | `--num-lookahead-slots` | `0` | Experimental scheduling config necessary for speculative decoding. This will be replaced by speculative config in the future; it is present to enable correctness tests until then. |
| 51 | `--seed` | `0` | Random seed for operations. |
| 52 | `--swap-space` | `4` | CPU swap space size (GiB) per GPU. |
| 53 | `--cpu-offload-gb` | `0` | The space in GiB to offload to CPU, per GPU. Default is 0, which means no offloading. Intuitively, this argument can be seen as a virtual way to increase the GPU memory size. For example, if you have one 24 GB GPU and set this to 10, virtually you can think of it as a 34 GB GPU. Then you can load a 13B model with BF16 weight,which requires at least 26GB GPU memory. Note that this requires fast CPU-GPU interconnect, as part of the model isloaded from CPU memory to GPU memory on the fly in each model forward pass. |
| 54 | `--gpu-memory-utilization` | `0.9` | The fraction of GPU memory to be used for the model executor, which can range from 0 to 1. For example, a value of 0.5 would imply 50%% GPU memory utilization. If unspecified, will use the default value of 0.9. |
| 55 | `--num-gpu-blocks-override` | `None` | If specified, ignore GPU profiling result and use this numberof GPU blocks. Used for testing preemption. |
| 56 | `--max-num-batched-tokens` | `None` | Maximum number of batched tokens per iteration. |
| 57 | `--max-num-seqs` | `256` | Maximum number of sequences per iteration. |
| 58 | `--max-logprobs` | `20` | Max number of log probs to return logprobs is specified in SamplingParams. |
| 59 | `--disable-log-stats` | `False` | Disable logging statistics. |
| 60 | `--quantization/-q` | `None` | Method used to quantize the weights. If None, we first check the `quantization_config` attribute in the model config file. If that is None, we assume the model weights are not quantized and use `dtype` to determine the data type of the weights. |
| 61 | `--rope-scaling` | `None` | RoPE scaling configuration in JSON format. For example, {"type":"dynamic","factor":2.0} |
| 62 | `--rope-theta` | `None` | RoPE theta. Use with `rope_scaling`. In some cases, changing the RoPE theta improves the performance of the scaled model. |
| 63 | `--enforce-eager` | `False` | Always use eager-mode PyTorch. If False, will use eager mode and CUDA graph in hybrid for maximal performance and flexibility. |
| 64 | `--max-context-len-to-capture` | `None` | Maximum context length covered by CUDA graphs. When a sequence has context length larger than this, we fall back to eager mode. (DEPRECATED. Use --max-seq-len-to-capture instead) |
| 65 | `--max-seq-len-to-capture` | `8192` | Maximum sequence length covered by CUDA graphs. When a sequence has context length larger than this, we fall back to eager mode. Additionally for encoder-decoder models, if the sequence length of the encoder input is larger than this, we fall back to the eager mode. |
| 66 | `--disable-custom-all-reduce` | `False` | See ParallelConfig. |
| 67 | `--tokenizer-pool-size` | `0` | Size of tokenizer pool to use for asynchronous tokenization. If 0, will use synchronous tokenization. |
| 68 | `--tokenizer-pool-type` | `ray` | Type of tokenizer pool to use for asynchronous tokenization. Ignored if tokenizer_pool_size is 0. |
| 69 | `--tokenizer-pool-extra-config` | `None` | Extra config for tokenizer pool. This should be a JSON string that will be parsed into a dictionary. Ignored if tokenizer_pool_size is 0. |
| 70 | `--limit-mm-per-prompt` | `None` | For each multimodal plugin, limit how many input instances to allow for each prompt. Expects a comma-separated list of items, e.g.: `image=16,video=2` allows a maximum of 16 images and 2 videos per prompt. Defaults to 1 for each modality. |
| 71 | `--mm-processor-kwargs` | `None` | Overrides for the multimodal input mapping/processing,e.g., image processor. For example: {"num_crops": 4}. |
| 72 | `--enable-lora` | `False` | If True, enable handling of LoRA adapters. |
| 73 | `--max-loras` | `1` | Max number of LoRAs in a single batch. |
| 74 | `--max-lora-rank` | `16` | Max LoRA rank. |
| 75 | `--lora-extra-vocab-size` | `256` | Maximum size of extra vocabulary that can be present in a LoRA adapter (added to the base model vocabulary). |
| 76 | `--lora-dtype` | `auto` | Data type for LoRA. If auto, will default to base model dtype. |
| 77 | `--long-lora-scaling-factors` | `None` | Specify multiple scaling factors (which can be different from base model scaling factor - see eg. Long LoRA) to allow for multiple LoRA adapters trained with those scaling factors to be used at the same time. If not specified, only adapters trained with the base model scaling factor are allowed. |
| 78 | `--max-cpu-loras` | `None` | Maximum number of LoRAs to store in CPU memory. Must be >= than max_num_seqs. Defaults to max_num_seqs. |
| 79 | `--fully-sharded-loras` | `False` | By default, only half of the LoRA computation is sharded with tensor parallelism. Enabling this will use the fully sharded layers. At high sequence length, max rank or tensor parallel size, this is likely faster. |
| 80 | `--enable-prompt-adapter` | `False` | If True, enable handling of PromptAdapters. |
| 81 | `--max-prompt-adapters` | `1` | Max number of PromptAdapters in a batch. |
| 82 | `--max-prompt-adapter-token` | `0` | Max number of PromptAdapters tokens |
| 83 | `--device` | `auto` | Device type for vLLM execution. |
| 84 | `--num-scheduler-steps` | `1` | Maximum number of forward steps per scheduler call. |
| 85 | `--multi-step-stream-outputs` | `True` | If False, then multi-step will stream outputs at the end of all steps |
| 86 | `--scheduler-delay-factor` | `0.0` | Apply a delay (of delay factor multiplied by previous prompt latency) before scheduling next prompt. |
| 87 | `--enable-chunked-prefill` | `None` | If set, the prefill requests can be chunked based on the max_num_batched_tokens. |
| 88 | `--speculative-model` | `None` | The name of the draft model to be used in speculative decoding. |
| 89 | `--speculative-model-quantization` | `None` | Method used to quantize the weights of speculative model. If None, we first check the `quantization_config` attribute in the model config file. If that is None, we assume the model weights are not quantized and use `dtype` to determine the data type of the weights. |
| 90 | `--num-speculative-tokens` | `None` | The number of speculative tokens to sample from the draft model in speculative decoding. |
| 91 | `--speculative-disable-mqa-scorer` | `False` | If set to True, the MQA scorer will be disabled in speculative  and fall back to batch expansion |
| 92 | `--speculative-draft-tensor-parallel-size/-spec-draft-tp` | `None` | Number of tensor parallel replicas for the draft model in speculative decoding. |
| 93 | `--speculative-max-model-len` | `None` | The maximum sequence length supported by the draft model. Sequences over this length will skip speculation. |
| 94 | `--speculative-disable-by-batch-size` | `None` | Disable speculative decoding for new incoming requests if the number of enqueue requests is larger than this value. |
| 95 | `--ngram-prompt-lookup-max` | `None` | Max size of window for ngram prompt lookup in speculative decoding. |
| 96 | `--ngram-prompt-lookup-min` | `None` | Min size of window for ngram prompt lookup in speculative decoding. |
| 97 | `--spec-decoding-acceptance-method` | `rejection_sampler` | Specify the acceptance method to use during draft token verification in speculative decoding. Two types of acceptance routines are supported: 1) RejectionSampler which does not allow changing the acceptance rate of draft tokens, 2) TypicalAcceptanceSampler which is configurable, allowing for a higher acceptance rate at the cost of lower quality, and vice versa. |
| 98 | `--typical-acceptance-sampler-posterior-threshold` | `None` | Set the lower bound threshold for the posterior probability of a token to be accepted. This threshold is used by the TypicalAcceptanceSampler to make sampling decisions during speculative decoding. Defaults to 0.09 |
| 99 | `--typical-acceptance-sampler-posterior-alpha` | `None` | A scaling factor for the entropy-based threshold for token acceptance in the TypicalAcceptanceSampler. Typically defaults to sqrt of --typical-acceptance-sampler-posterior-threshold i.e. 0.3 |
| 100 | `--disable-logprobs-during-spec-decoding` | `None` | If set to True, token log probabilities are not returned during speculative decoding. If set to False, log probabilities are returned according to the settings in SamplingParams. If not specified, it defaults to True. Disabling log probabilities during speculative decoding reduces latency by skipping logprob calculation in proposal sampling, target sampling, and after accepted tokens are determined. |
| 101 | `--model-loader-extra-config` | `None` | Extra config for model loader. This will be passed to the model loader corresponding to the chosen load_format. This should be a JSON string that will be parsed into a dictionary. |
| 102 | `--ignore-patterns` | `[]` | The pattern(s) to ignore when loading the model.Default to 'original/**/*' to avoid repeated loading of llama's checkpoints. |
| 103 | `--preemption-mode` | `None` | If 'recompute', the engine performs preemption by recomputing; If 'swap', the engine performs preemption by block swapping. |
| 104 | `--served-model-name` | `None` | The model name(s) used in the API. If multiple names are provided, the server will respond to any of the provided names. The model name in the model field of a response will be the first name in this list. If not specified, the model name will be the same as the `--model` argument. Noted that this name(s)will also be used in `model_name` tag content of prometheus metrics, if multiple names provided, metricstag will take the first one. |
| 105 | `--qlora-adapter-name-or-path` | `None` | Name or path of the QLoRA adapter. |
| 106 | `--otlp-traces-endpoint` | `None` | Target URL to which OpenTelemetry traces will be sent. |
| 107 | `--collect-detailed-traces` | `None` | Valid choices are model,worker,all. It makes sense to set this only if --otlp-traces-endpoint is set. If set, it will collect detailed traces for the specified modules. This involves use of possibly costly and or blocking operations and hence might have a performance impact. |
| 108 | `--disable-async-output-proc` | `False` | Disable async output processing. This may result in lower performance. |
| 109 | `--override-neuron-config` | `None` | Override or set neuron device configuration. e.g. {"cast_logits_dtype": "bloat16"}.' |
| 110 | `--scheduling-policy` | `fcfs` | The scheduling policy to use. "fcfs" (first come first served, i.e. requests are handled in order of arrival; default) or "priority" (requests are handled based on given priority (lower value means earlier handling) and time of arrival deciding any ties). |
| 111 | `--disable-log-requests` | `False` | Disable logging requests. |
| 112 | `--max-log-len` | `None` | Max number of prompt characters or prompt ID numbers being printed in log.  Default: Unlimited |
| 113 | `--disable-fastapi-docs` | `False` | Disable FastAPI's OpenAPI schema, Swagger UI, and ReDoc endpoint |