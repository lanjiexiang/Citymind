# -*- coding: utf-8 -*-
import os
import io
import time
import shutil
import traceback
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql
from docx import Document
import io
import json
from PIL import Image
import numpy as np
import decimal

# 外置函数引入
import banana   
import doubao
import qwenVLLM
from qwenVLLM import analyze_images
import qwenLLM
from qwenLLM import summarize_prompt

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "saved_screenshots")
GENERATED_DIR = os.path.join(BASE_DIR, "static", "generated")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
app = Flask(__name__, static_folder="static")
CORS(app)
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '980908',
    'database': 'TEI',
    'charset': 'utf8mb4'
}
db_connection = None

# 保存图片base64编码
def _save_base64_image(data_url: str, dst_path: str):
    if not data_url:
        raise ValueError("empty data")
    header, b64 = data_url.split(",", 1)
    if "base64" in header:
        data = base64.b64decode(b64)
    else:
        data = b64.encode("utf-8")
        
    with open(dst_path, "wb") as f:
        f.write(data)
    return dst_path


#处理多边形选区图片
def process_polygon_image(data_url: str, polygon_data: dict):
    # 解码base64图片
    header, b64 = data_url.split(",", 1)
    if "base64" in header:
        image_data = base64.b64decode(b64)
    else:
        image_data = b64.encode("utf-8")
        
    # 转换保存为png格式
    img = Image.open(io.BytesIO(image_data))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    temp_path = os.path.join(SAVE_DIR, "temp_polygon.png")
    img.save(temp_path, 'PNG', optimize=True, quality=95)
    return temp_path



#---------------------------------------------------------------------------------
#-----------------------------------重点路由设计-----------------------------------
#---------------------------------------------------------------------------------

# 保存地图截图
@app.route("/save-screenshot", methods=["POST"])
def save_screenshot():
    try:
        data = request.get_json(force=True)
        data_url = data.get("image")
        role = data.get("role", "").strip().lower()
        # 扩展允许的角色列表，包含顶视图图片
        allowed_roles = ("big", "small", "standard_base", "big_over", "small_over")
        if role not in allowed_roles:
            return jsonify({"ok": False, "error": f"role must be one of {allowed_roles}"}), 400
        
        # 保存大地图（卫星图视角）
        if role == "big":
            fname = f"big.png"
            dst = os.path.join(SAVE_DIR, fname)
            _save_base64_image(data_url, dst)
            return jsonify({"ok": True})
        
        # 保存顶视图大地图
        elif role == "big_over":
            fname = f"big_over.png"
            dst = os.path.join(SAVE_DIR, fname)
            _save_base64_image(data_url, dst)
            return jsonify({"ok": True})
        
        # 保存多边形基地选区（卫星图视角）
        elif role == "small":
            polygon_data = {
                'polygon_points': data.get('polygon_points', []),
                'polygon_screen_points': data.get('polygon_screen_points', []),
                'bounding_box': data.get('bounding_box', {})
            }
            temp_path = process_polygon_image(data_url, polygon_data)
            fname = f"small.png"
            dst = os.path.join(SAVE_DIR, fname)
            
            # 移动临时文件到最终位置
            if os.path.exists(temp_path):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(temp_path, dst)
            return jsonify({"ok": True})
        
        # 保存顶视图基地选区
        elif role == "small_over":
            polygon_data = {
                'polygon_points': data.get('polygon_points', []),
                'polygon_screen_points': data.get('polygon_screen_points', []),
                'bounding_box': data.get('bounding_box', {})
            }
            temp_path = process_polygon_image(data_url, polygon_data)
            fname = f"small_over.png"
            dst = os.path.join(SAVE_DIR, fname)
            
            # 移动临时文件到最终位置
            if os.path.exists(temp_path):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(temp_path, dst)
            return jsonify({"ok": True})
        
        # 保存三维地图基地选区
        elif role == "standard_base":
            fname = f"standard_base.png"
            dst = os.path.join(SAVE_DIR, fname)
            _save_base64_image(data_url, dst)
            return jsonify({"ok": True})
                
    except Exception as e:
        print(f"保存截图时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# 生成规划草图
@app.route("/generate-sketch", methods=["POST"])
def generate_sketch():
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt")
    pro = data.get("pro", False)
        
    #图片路径
    big_path = os.path.join(SAVE_DIR, "big.png")
    small_path = os.path.join(SAVE_DIR, "small.png")
    standard_base_path = os.path.join(SAVE_DIR, "standard_base.png")
        
    # 草图生成提示词工程
    complete_prompt = f"""
        你是一名专业的城市规划设计师，需要生成一张关于保利悦活荟区域的**专业手绘风格三维规划草图**。生成过程必须严格遵循以下分层技术指令，确保核心区与周边区域既有视觉区分又能无缝融合。

        **一、核心指令：区域分层渲染系统**
        请严格按照以下三个区域定义，应用截然不同的渲染策略，并确保区域之间通过**视觉渐变**实现自然过渡，严禁出现生硬的切割线。

        1.  **核心区（基地区域 - 重点渲染）**
            *   **范围**：严格限定在参考图2（规划基地卫星图）的边界线之内。
            *   **视觉要求**：进行**柔和的水彩风格颜色渲染**。使用淡雅的色块区分不同功能区块（如建筑屋顶、绿地、广场），颜色作为底衬，不能覆盖手绘线稿。细节密度高，需体现建筑立面窗扇、屋顶结构和景观纹理。
            *   **关键词**: `detailed coloring, watercolor wash, subtle tones, architectural rendering`.

        2.  **过渡区（视觉缓冲带 - 关键区域）**
            *   **范围**：核心区边界向外自然扩展约50-100米的带状区域，由于参考图2即基地所在多边形区域是用户手绘的，可能会存在一定的误差或者突兀的地方，你需要润色调整一下基地的区域。
            *   **视觉要求**：**核心区色彩的衰减区与非基地区域细节的起点**。本区域**不进行颜色渲染**，核心区的色彩在此应**自然减淡、饱和度降低**，如同水彩画中的湿接渐变。建筑表现为简化的体块，使用柔和的单色阴影体现体积感，路网清晰连续。
            *   **目标**：实现从核心区到外围区的视觉引导，避免任何形式的边界线。
            *   **关键词**: `natural blending, color fade-out, simplified massing, basic road network`.

        3.  **外围区（上下文环境 - 简化表现）**
            *   **范围**：过渡区以外的所有部分。
            *   **视觉要求**：**完全无颜色渲染，极度简化**。建筑仅用最简化的轮廓或体块（silhouettes）表示，核心任务是清晰、连续地描绘出**连接至核心区的道路网络**。整体细节密度低，呈现"幽灵线"效果，避免分散对核心区的注意力。
            *   **关键词**: `contextual silhouettes, minimal detail, clear road connections, ghosted lines`.

        **二、基底结构与风格约束**
        *   **空间结构**：**严格锁定**参考图3（标准基底三维图）的俯瞰视角、透视灭点、道路路径及建筑基底轮廓。禁止修改其空间拓扑关系。
        *   **核心风格**：`architectural sketch, hand-drawn, aerial perspective, loose strokes, pen and ink hatching, paper texture`.
        *   **色彩模式**：核心区外，整体画面保持单色或浅色调，以确保核心区的颜色成为视觉焦点。

        **三、负面约束 (Negative Prompt)**
        必须排除以下元素，以确保输出质量：
        - `satellite imagery, aerial photography, black borders, watermarks, text labels`
        - `photorealistic, 3D rendering, perfect geometry, CAD lines`
        - `vibrant colors, high saturation` (核心区颜色也应柔和)
        - `hard edges, sharp cuts between zones, sudden color changes` (确保过渡自然)
        - `texture overlay from reference images`

        **四、个性化设计集成**
        在严格遵守上述结构锁定的前提下，融入以下设计意图：{prompt}

        **五、输出规格与质量控制**
        - **分辨率**：建议2048x2048或更高，确保线条清晰。
        - **格式**：PNG。
        - **保真度**：保持手绘笔触的自然感和画面的艺术性。
        - **验证清单**：
            ☑☑ 核心区有颜色渲染，外围区无线稿但路网清晰。
            ☑☑ 核心区与外围区通过过渡带自然融合，无硬边界。
            ☑☑ 无卫星图纹理或标注文字残留。
            ☑☑ 透视与参考图3完全一致。

        请根据以上所有要求，生成一张单张、完整的规划草图。
        """

    try:
            # 调用banana生成规划草图
            image_paths = [big_path, small_path, standard_base_path]
            banana.nanobanana_generate(complete_prompt, image_paths, pro=pro)
            generated_folder = GENERATED_DIR
            if not os.path.exists(generated_folder):
                os.makedirs(generated_folder)
            time.sleep(5)
            png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
            png_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
            latest_file = png_files[0]
            source_path = os.path.join(generated_folder, latest_file)
            timestamp = int(time.time() * 1000)
            pro_suffix = "_pro" if pro else ""
            fname1 = f"generated_{timestamp}{pro_suffix}.png"
            dst1 = os.path.join(GENERATED_DIR, fname1)
            if os.path.exists(source_path):
                if os.path.exists(dst1):
                    os.remove(dst1)
                shutil.move(source_path, dst1)
            image_url1 = f"/static/generated/{fname1}"
            
            # 生成平视图
            print("开始生成平视图...")
            ortho_prompt = """帮我生成图片：# 任务核心：视角转换与场景重建将提供的基地平面图（草图）转换为一张人眼高度、平视视角的建筑场景表现图。注意严厉禁止新增建筑或者修改原有的建筑元素。# 1. 核心视角与构图描述观察视角：观察点位于基地主要道路前（可以识别基地的长边），保证观察基地是正视而不是斜视。视线方向平行于地面，平视建筑群，以展现建筑立面的完整性和群体关系。镜头特性：模拟中焦镜头（35mm-50mm），产生自然、轻微的透视感，确保垂直线条垂直，水平线条汇聚极缓，避免夸张畸变。画面构图平稳，建筑作为主体突出。严格注意镜头够宽但不得是弯曲的广角镜头，能够展现整个基地区域（有色彩着重渲染的部分）。同时镜头足够低，保证镜头内大部分是基地区域（有色彩着重渲染的部分），镜头正前方和后方不要有过多镜头外的区域，注意保证镜头和基地的建筑群高度相近即可，保持轻微仰视或者平视整个基地，保证基地后方不要有过多区域。# 2. 对原始设计要素的严格继承与转换几何与布局：严格依据原平面图的空间布局、建筑轮廓、道路走向和景观位置进行三维重建。所有要素的相对位置、尺寸比例必须精准对应原图。* 色彩基调：不改变原图的色彩搭配意图。# 3. 负面约束（禁止项）no aerial view, no bird's-eye view, no isometric projection, (禁止鸟瞰/轴测) no exaggerated perspective, no fisheye effect, (禁止夸张透视/鱼眼) no cartoon, no sketch, no watercolor, no artistic filter, (禁止非写实风格) no people, no cars, no added decorations, (禁止添加无关物品) no change to layout, no recolor of buildings, (禁止改变布局和主体颜色) no blurry background, no depth of field blur, (禁止景深模糊) no text labels, no "AI generated" watermark. (禁止文字标签和水印)不得新增建筑或者修改原有的建筑元素。禁止添加一个人在道路上表示人眼高度# 5. 交付要求输出单张高清图像，呈现一个从基地前方、人眼高度观看的、真实且沉稳的现代化建筑群落场景。"""
            
            downloaded_paths, generated_filenames = doubao.generate([dst1], ortho_prompt)
            fname2 = generated_filenames[0]
            image_url2 = f"/static/generated/{fname2}"
            print("平视图生成完成")
            
            # 生成俯视图
            print("开始生成俯视图...")
            top_view_prompt = """帮我生成图片： 你是一名精通建筑制图规范的城市规划设计师。你的唯一任务是将保利悦活荟基地参考图，进行纯粹的视角转换——生成从正上方90°垂直俯视的正交投影三维俯视图。 【绝对约束：零增删与100%保真原则】 转换过程仅涉及投影方式变更，严禁对原图内容进行任何取舍、简化、创造或风格化： 禁止删除任何建筑、构筑物、道路线段、景观元素 禁止新增任何原图不存在的元素 禁止合并或拆分原图中的任何轮廓 必须100%保留所有元素的轮廓、比例、相对位置及色彩属性，确保拓扑关系、材质表现与原图分毫不差 严禁主观改变原图中任何建筑元素的色彩、明暗或材质特征 【核心视角与投影指令】 观察点：固定于基地正上方，镜头光轴与地面绝对90°垂直 投影方式：严格正交投影，消除透视变形，所有水平线条保持平行且比例一致 画面定向：基地较长边必须与图片底边绝对平行，严禁任何旋转或倾斜 画面范围：完整包含原图所有内容，严禁裁切或重新构图 【纯粹视觉表现要求】 线条层级：手绘风格，通过线宽区分元素层级（建筑轮廓最粗、道路次之、景观最细），所有线条必须基于原图轮廓精准tracing 色彩处理：所有元素（尤其是建筑）的色彩必须与原始参考图保持完全一致，仅允许通过整体亮度-10%的方式对基地主体建筑范围进行视觉强调，使其与场地环境形成图底分离，但不得改变任何元素的色相、饱和度或材质质感 高度表达：通过统一方向轻微阴影体现建筑高度差异，但不得干扰平面轮廓清晰度 文字信息：严禁添加任何文字标注，保持图面纯粹。"""
            
            downloaded_paths, generated_filenames = doubao.generate([dst1], top_view_prompt)
            fname3 = generated_filenames[0]
            image_url3 = f"/static/generated/{fname3}"
            print("俯视图生成完成")
            
            # 返回不同视角的基地草图
            return jsonify({
                "ok": True, 
                "images": [image_url1, image_url2, image_url3],  
                "filenames": [fname1, fname2, fname3,],     
                "pro_version": pro
            })
                    
    except Exception as e:
            print(f"生成草图失败: {e}")
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"生成草图失败: {str(e)}"}), 500
        



# 修改规划草图
@app.route("/suggest-edits", methods=["POST"])
def suggest_edits():
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt")
    reference_image_url = data.get("reference_image")
    filename = os.path.basename(reference_image_url)
    reference_image_path = os.path.join(GENERATED_DIR, filename)
        
    # 草图修改提示词工程
    new_prompt = f"""
        你是一名专业的城市规划设计师，负责优化一张手绘风格的城市规划草图。

        # 核心修改区域（严格限定）
        请将所有的修改操作**严格限定**在图片中已有**明显色彩渲染的区域**（即“基地”内部）。基地之外的区域（如空白处、未上色区域）请务必保持原样，不得进行任何改动或添加元素。

        # 具体修改要求
        {prompt}

        # 风格与执行原则
        1.  **风格一致性**：修改必须基于原始草图，优化后的部分在笔触、线条和整体美学上需与草图的手绘风格无缝融合。
        2.  **专业性**：优化方案需符合城市规划的专业规范，布局合理。
        3.  **迭代优化**：请在现有草图基础上进行改进，而非彻底重新创作。

        请根据以上要求，对指定基地区域进行专业的规划修改。
        """
    try:  
        image_paths = [reference_image_path]
        banana.nanobanana_generate(new_prompt, image_paths, pro=False)
        generated_folder = GENERATED_DIR
        time.sleep(5)

        # 寻找草图修改结果
        png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
        if png_files:
            latest_file = png_files[0]
            source_path = os.path.join(generated_folder, latest_file)
            timestamp = int(time.time() * 1000)
            fname = f"modified_{timestamp}.png"
            dst = os.path.join(GENERATED_DIR, fname)
            if os.path.exists(source_path):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(source_path, dst)
                image_url = f"/static/generated/{fname}"
                return jsonify({
                    "ok": True, 
                    "images": [image_url],  
                    "filenames": [fname],
                    "pro_version": False
                })
                
    except Exception as e:
        print(f"banana修改草图失败: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"草图修改失败: {str(e)}"}), 500
    

# AI规划师分析
@app.route("/analyze-with-ai", methods=["POST"])
def analyze_with_ai():
    try:
        # 获取前端数据
        data = request.get_json(force=True) or {}
        style_suggestion = data.get("style_suggestion", "")
        survey_summary = data.get("survey_summary", "")  
        economic_indicators_str = data.get("economic_indicators_str", "")  
    
        
        big_path = os.path.join(SAVE_DIR, "big.png")
        small_path = os.path.join(SAVE_DIR, "small.png")
        standard_base_path = os.path.join(SAVE_DIR, "standard_base.png")

        # 构建经济技术指标描述
        economic_analysis = ""
        if economic_indicators_str:
            print("检测到经济指标字符串数据")
            economic_analysis = f"""
4. **经济技术指标分析**：
{economic_indicators_str}
请基于这些经济技术指标，分析项目的经济可行性和开发强度合理性。"""
        else:
            print("未接收到经济指标字符串数据")

        # 构建分析提示词工程
        base_prompt = """现在你是一名专业的城市规划设计师和建筑分析师。请基于以下三张图片进行综合分析，按照以下顺序提供专业分析：

1. **区位分析**：基于大地图分析规划基地在区域中的位置优势、交通可达性、周边环境关系和发展潜力

2. **建筑体系结构分析**：基于三维地图分析现有建筑的布局模式、高度分布、体量关系、空间组织和结构特点

3. **功能分区评估**：结合卫星图和三维地图，识别当前的功能分区布局，分析各功能区之间的衔接关系、流线组织和功能合理性"""

        # 添加经济技术指标分析
        if economic_indicators_str:
            base_prompt += economic_analysis

        # 添加群众需求整合
        if survey_summary:
            section_num = 4 if economic_indicators_str else 4
            base_prompt += f"""
{section_num}. **群众需求整合**：结合调研报告中的群众建议：{survey_summary}，分析如何将民意需求融入规划方案"""
            
        # 添加个性化设计导向
        if style_suggestion:
            section_num = 5 if (economic_indicators_str or survey_summary) else 4
            prompt = f"""{base_prompt}
{section_num}. **个性化设计导向**：在分析时请特别考虑用户提供的设计倾向：{style_suggestion}

请按照上述顺序提供专业的分析报告，每个部分都要有具体的分析内容和建设性建议。"""
        else:
            prompt = f"""{base_prompt}

请按照上述顺序提供专业的分析报告，每个部分都要有具体的分析内容和建设性建议。"""
            
        # 调用qwenVLLM分析规划
        analysis_result = analyze_images([big_path, small_path, standard_base_path], prompt)
        return jsonify({
            "ok": True, 
            "analysis": analysis_result
        })
    
    except Exception as e:
        print(f"AI分析时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# 总结分析助手
@app.route("/summarize-prompt", methods=["POST"])
def summarize_prompt():
    try:
        # 获取前端数据
        data = request.get_json(force=True) or {}
        analysis = data.get("analysis")
        small_path = os.path.join(SAVE_DIR, "small.png")
        standard_base_path = os.path.join(SAVE_DIR, "standard_base.png")

        # 总结提示词
        prompt = f"""
现在你是具备城市设计规划专业能力的总结助手，请完成以下任务：
1. 基于提供的AI分析结果【{analysis}】、基地卫星地图（图片1）和基地三维地图（图片2）；
2. 生成用于AI图像生成工具的修改型prompt，需重点突出：
   - 建筑结构的显著调整（如布局、尺度、空间组织）；
   - 建筑风格的明确变化（如现代/新中式/工业风等具体风格）；
   - 符合城市设计规划的基本逻辑（如功能分区、空间肌理、景观衔接）；
3. 要求：语言简洁、指令明确，仅用于修改基地相关图像；
4. 输出格式严格为：总结的prompt为：[你的生成内容]（仅保留此格式，无额外文字）。
        """.strip() 

        # 调用qwenVLLM生成总结
        summarized_prompt = analyze_images([small_path, standard_base_path], prompt)
        
        if summarized_prompt is None:
            return jsonify({"ok": False, "error": "总结生成失败"}), 500
        
        return jsonify({
            "ok": True, 
            "summarized_prompt": summarized_prompt
        })

    except Exception as e:
        print(f"总结prompt时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# 分析调研报告
@app.route("/summarize-report", methods=["POST"])
def summarize_report():
    try:
        # 读取docx文件内容
        file = request.files['docx']
        doc = Document(io.BytesIO(file.read()))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        content = ' '.join(full_text) 

        # 报告分析提示词
        prompt = f"""
现在你是具备城市更新专业背景的文档总结助手，请完成以下任务：
1. 分析素材：城市更新项目基地周边群众的访谈记录【{content}】；
2. 总结要求：
   - 核心聚焦：提取群众对该片区城市更新的**具体有意义的建议**（而非情绪/描述）；
   - 结构形式：用中文数字分点（如1.、2.、3.）；
   - 内容维度：优先覆盖城市更新核心方向（基础设施、空间功能、文化保留、生态环境、民生配套等）；
3. 输出要求：仅返回分点总结内容，无额外开场白/结束语。
        """.strip()  # 去除多余换行和空格
        #调用qwenLLM总结报告
        summary = qwenLLM.summarize_prompt(prompt) 
        if summary is None:
            return jsonify({"ok": False, "error": "总结生成失败"}), 500
        return jsonify({
            "ok": True, 
            "summary": summary
        })
    
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# 功能分区总结
@app.route("/generate-zoning-prompt", methods=["POST"])
def generate_zoning_prompt():
    try:
        # 获取前端数据
        data = request.get_json(force=True) or {}
        analysis = data.get("analysis")
        small_over_path = os.path.join(SAVE_DIR, "small_over.png")
        
        
        # 构建提示词
        prompt = f"""
现在你是具备城市设计规划专业能力的功能分区总结助手，请基于以下信息完成功能分区分析：

【输入信息】
1. 参考图像：基地顶视图（small_over.png），展示基地的建筑结构体系
2. AI分析建议：{analysis}

【任务要求】
请基于参考图像的基地建筑结构体系和AI分析建议，总结出具体的功能分区修改方案：

1. **功能分区布局**：
   - 明确各功能区在基地内的方位分布（上/下/左/右/左上/右上/左下/右下）
   - 说明每个功能区的核心功能和预期用途
   - 估算各功能区的相对面积占比

2. **分区衔接关系**：
   - 分析各功能区之间的流线组织和衔接方式
   - 说明功能分区的主次层级关系
   - 提出合理的过渡和缓冲区域设置

3. **基于建筑结构的调整**：
   - 结合现有建筑体系提出功能分区优化建议
   - 确保功能分区与建筑空间肌理相协调
   - 考虑景观绿化和公共空间的合理分布

4. **输出要求**：
   - 语言简洁专业，聚焦功能分区方案，字数不能太多，用总结性的结论概括
   - 提供可执行的具体建议
   - 格式：用清晰的条目列出功能分区方案
        """.strip()

        # 调用qwenVLLM生成分区总结
        zoning_prompt = analyze_images([small_over_path], prompt)
        if zoning_prompt is None:
            return jsonify({"ok": False, "error": "分区总结生成失败"}), 500
        return jsonify({
            "ok": True, 
            "zoning_prompt": zoning_prompt
        })

    except Exception as e:
        print(f"生成功能分区提示词时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# 生成功能分区图
@app.route("/generate-zoning-sketch", methods=["POST"])
def generate_zoning_sketch():
    try:
        # 获取前端数据
        data = request.get_json(force=True) or {}
        content_text = data.get("content_text")
        big_over_path = os.path.join(SAVE_DIR, "big_over.png")
        small_over_path = os.path.join(SAVE_DIR, "small_over.png")
        
        # 功能分区图提示词
        prompt = f"""
**Role**: 专业建筑规划平面设计师，精通手绘风格功能分区图绘制

**核心指令**: **保持顶视平行视角**，精准识别图片2的闭合多边形边界作为**唯一**绘制区域（WORK_ZONE_LOCKED），严禁越界。

---

**输入说明**:
- **图片1**: 仅参考宏观布局，**禁止**对其任何区域进行功能分区或填色
- **图片2**: 包含明确标注的闭合多边形边界，**仅在此边界内**进行功能分区

---

**绘制流程（必须按顺序）**:

**Step 1: 多边形边界识别与锁定**
- **绝对前提**: 识别图2中的多边形闭合边界，标记为WORK_ZONE_LOCKED
- **未确认边界前严禁后续操作**

**Step 2: WORK_ZONE_LOCKED内部绘制**
- ✅ 高饱和度色块填充各功能区（色彩对比强烈，**填充至边界线即止**）
- ✅ 手绘质感线条绘制建筑结构框架（墙体、核心筒）
- ✅ 英文标注区域名称（简洁无衬线字体）
- **位置模糊时**: 布局在内部空置区域，**严禁因布局需要扩大边界**

**Step 3: WORK_ZONE_LOCKED外部处理**
- ❌ **严禁**: 功能分区、色彩填充、英文标注
- ✅ 仅用极简手绘线条勾勒周边建筑外轮廓

---

**【功能分区修改方案】**
{content_text}

---

**核心规范**:

**基地内部（WORK_ZONE_LOCKED）**:
- 所有元素**100%**位于边界内
- 必须包含: 高饱和色块 + 英文标注 + 结构框架
- **严格顶视视角**，线条垂直投影

**基地外部**:
- 仅极简线条勾勒，无填充无标注

**整体风格**: 手绘插画风格，内部色彩鲜明 vs 外部极简线条，边界清晰

---

**严禁事项**:
- ❌ **绝对禁止**边界外色彩填充或标注，不需要标注地点等文字（只能有标注功能分区部分）
- ❌ **绝对禁止**因分区过大而"溢出"边界
- 边界模糊时**宁可保守缩小**，不可扩大

---

**输出**: 单张高清平面图，内部鲜明色块 + 外部极简线条

**生成前验证**:
- □ 所有色块、标注均在边界内？
- □ 外部无任何填充或标注？
- □ **严格顶视视角**？

确认无误后输出。
        """.strip()

        # 调用banana生成功能分区图
        image_paths = [big_over_path, small_over_path]
        banana.nanobanana_generate(prompt, image_paths, pro=False)
        generated_folder = GENERATED_DIR
        time.sleep(5)
        
        # 寻找生成结果
        png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
        
        if png_files:
            latest_file = png_files[0]
            source_path = os.path.join(generated_folder, latest_file)
            timestamp = int(time.time() * 1000)
            fname = f"zoning_{timestamp}.png"
            dst = os.path.join(GENERATED_DIR, fname)
            
            if os.path.exists(source_path):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(source_path, dst)
                image_url = f"/static/generated/{fname}"
                
                return jsonify({
                    "ok": True, 
                    "images": [image_url],  
                    "filenames": [fname]
                })
        else:
            return jsonify({"ok": False, "error": "未找到生成的图片"}), 500
                
    except Exception as e:
        print(f"生成功能分区图失败: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"功能分区图生成失败: {str(e)}"}), 500



# 获取技术经济指标数据库
@app.route("/get-economic-indicators", methods=["GET"])
def get_economic_indicators():
    try:
        with db_connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM economic_indicators ORDER BY created_at DESC LIMIT 1"
            cursor.execute(sql)
            data = cursor.fetchone()
            
            if data:
                # 转换Decimal类型为float以便JSON序列化
                for key, value in data.items():
                    if isinstance(value, decimal.Decimal):
                        data[key] = float(value)
                return jsonify({"ok": True, "data": data})
            else:
                return jsonify({"ok": False, "error": "未找到技术经济指标数据"}), 404
    except Exception as e:
        print(f"获取技术经济指标数据错误: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500



#运行主函数
if __name__ == "__main__":
    try:
        db_connection = pymysql.connect(**db_config) 
        print("🔌 成功连接到MySQL数据库") 
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        db_connection = None
    print("Starting server on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)