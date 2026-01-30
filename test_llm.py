import utils.vlm_transportation.to_llama_server as say
for chunk in say.llm_requests("你好，请介绍一下你自己"):
    if content := chunk['choices'][0].get('delta', {}).get('content'):
        print(content, end='', flush=True)