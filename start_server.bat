3rd-part\llamacpp-cuda124\llama-server.exe ^
  --model model/vision_llm/Qwen3-VL-8B-abliterated-v2.0/Qwen3-VL-8B-Instruct-abliterated-v2.0.Q6_K.gguf ^
  --mmproj model/vision_llm/Qwen3-VL-8B-abliterated-v2.0/Qwen3-VL-8B-Instruct-abliterated-v2.0.mmproj-Q8_0.gguf ^
  --port 8080 ^
  --host 127.0.0.1 ^
  --ctx-size 20480 ^
  --n-gpu-layers 37 ^
  --threads 1 ^
  --n-predict 4096

pause