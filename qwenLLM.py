import os
from openai import OpenAI

#总结文本助手
def summarize_prompt(prompt="你是谁？"):
    client = OpenAI(
        api_key="sk-c9abe051e7af488093cec76619576d76",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}, 
        ]
    )
    return completion.model_dump_json()



# 示例
if __name__ == "__main__":
    result = summarize_prompt()
    print(result)
    
