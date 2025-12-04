#!/bin/bash
set -e

echo "🚀 Starting Diary API Server..."

# ✅ Ollama 대기 로직 제거 (Ollama 없이 실행)
# Ollama를 사용하지 않고 로컬에서 실행 중이므로
# if ! ollama list | grep -q "qwen2.5"; then
#   echo "🚀 Model not found. Installing..."
#   ollama pull qwen2.5:7b
# else
#   echo "✅ Model already installed"
# fi

# Uvicorn 실행
echo "🎯 Starting Uvicorn on port 8002..."
exec uvicorn main:app --host 0.0.0.0 --port 8002 --reload


