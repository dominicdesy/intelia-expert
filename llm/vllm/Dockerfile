# vLLM Dockerfile for Intelia Llama 3.1 8B
# Optimized for NVIDIA GPU deployment

FROM vllm/vllm-openai:latest

# Set environment variables
ENV MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
ENV TENSOR_PARALLEL_SIZE=1
ENV MAX_MODEL_LEN=4096
ENV GPU_MEMORY_UTILIZATION=0.9
ENV QUANTIZATION=""

# Optional: Download model at build time (faster startup)
# Uncomment if you want to bake the model into the image
# RUN huggingface-cli download ${MODEL_NAME}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start vLLM server with OpenAI-compatible API
CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--model", "${MODEL_NAME}", \
     "--tensor-parallel-size", "${TENSOR_PARALLEL_SIZE}", \
     "--max-model-len", "${MAX_MODEL_LEN}", \
     "--gpu-memory-utilization", "${GPU_MEMORY_UTILIZATION}"]
