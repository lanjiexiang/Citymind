import os
from openai import OpenAI
import base64

#图像分析助手
def analyze_images(image_paths, prompt="图中描绘的是什么景象?"):
    #配置
    client = OpenAI(
        api_key="sk-c9abe051e7af488093cec76619576d76",  
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    content = []
    
    # 添加图片
    for image_path in image_paths:
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        except Exception as e:
            print(f"读取图片失败: {image_path}, 错误: {e}")
            return None
    
    # 添加prompt
    content.append({"type": "text", "text": prompt})
    
    # 调用模型
    try:
        completion = client.chat.completions.create(
            model="qwen3-vl-plus",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"调用API失败: {e}")
        return None



# 示例
if __name__ == "__main__":
    image_paths = ["C:\\Users\\Administrator\\Desktop\\1.jpg"]
    result = analyze_images(image_paths)
    print("分析结果:", result)
