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
import ezdxf
import fitz
import cv2
import numpy as np
import json
import tempfile
from shapely.geometry import Polygon, LineString
from shapely.ops import polygonize, unary_union


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


#---------------------------------------------------------------------------------
#-----------------------------------地图截图与CAD相关------------------------------
#---------------------------------------------------------------------------------


def _normalize_coords(coords, bounds):
    """将坐标归一化到 0-1 范围"""
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y

    if width == 0 or height == 0:
        return coords

    normalized = []
    for x, y in coords:
        nx = (x - min_x) / width
        ny = 1 - (y - min_y) / height  # Y轴翻转（CAD坐标系Y向上）
        normalized.append([nx, ny])

    return normalized


def _extract_dxf_polygons(file_path, layer_filter=None):
    """
    从 DXF 文件提取多边形轮廓
    返回：polygons: [{coordinates: [[nx,ny]...], type, area_ratio}], bounds
    """
    if ezdxf is None:
        raise RuntimeError("服务器未安装 ezdxf，无法解析 DXF，请先安装 ezdxf 或上传 PNG 截图走轮廓识别")

    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    all_coords = []
    lines = []
    polygons_raw = []

    # 红线常见图层名称
    redline_layers = layer_filter or [
        "红线",
        "redline",
        "boundary",
        "用地红线",
        "基地红线",
        "用地范围",
        "规划红线",
        "建设用地",
        "site",
        "plot",
        "地块",
    ]

    def should_include(entity):
        if not layer_filter:
            return True
        layer = (entity.dxf.layer or "").lower()
        return any(kw.lower() in layer for kw in redline_layers)

    for entity in msp:
        if not should_include(entity):
            continue

        coords = []

        if entity.dxftype() == "LINE":
            start = (entity.dxf.start.x, entity.dxf.start.y)
            end = (entity.dxf.end.x, entity.dxf.end.y)
            lines.append([start, end])
            coords = [start, end]

        elif entity.dxftype() == "LWPOLYLINE":
            coords = [(p[0], p[1]) for p in entity.get_points()]
            if entity.closed:
                polygons_raw.append(coords)
            else:
                lines.append(coords)

        elif entity.dxftype() == "POLYLINE":
            coords = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            if entity.is_closed:
                polygons_raw.append(coords)
            else:
                lines.append(coords)

        elif entity.dxftype() == "CIRCLE":
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            angles = np.linspace(0, 2 * np.pi, 33)[:-1]
            coords = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in angles]
            polygons_raw.append(coords)

        elif entity.dxftype() == "ELLIPSE":
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            major = entity.dxf.major_axis
            ratio = entity.dxf.ratio
            angles = np.linspace(0, 2 * np.pi, 33)[:-1]
            coords = [
                (cx + major.x * np.cos(a) - major.y * ratio * np.sin(a),
                 cy + major.y * np.cos(a) + major.x * ratio * np.sin(a))
                for a in angles
            ]
            polygons_raw.append(coords)

        elif entity.dxftype() == "SPLINE":
            try:
                coords = [(p.x, p.y) for p in entity.flattening(0.1)]
                if len(coords) > 2:
                    lines.append(coords)
            except Exception:
                pass

        elif entity.dxftype() == "HATCH":
            for path in entity.paths:
                if hasattr(path, "vertices"):
                    coords = [(v.x, v.y) for v in path.vertices]
                    if len(coords) >= 3:
                        polygons_raw.append(coords)

        all_coords.extend(coords)

    # 尝试将未闭合的线段组合成多边形
    if lines and not polygons_raw and Polygon is not None:
        try:
            line_strings = []
            for line in lines:
                if len(line) >= 2:
                    line_strings.append(LineString(line))

            merged = unary_union(line_strings)
            polys = list(polygonize(merged))

            for poly in polys:
                if poly.is_valid and poly.area > 0:
                    coords = list(poly.exterior.coords)[:-1]
                    polygons_raw.append(coords)
        except Exception as e:
            print(f"线段合并失败: {e}")

    if all_coords:
        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        bounds = (min(xs), min(ys), max(xs), max(ys))
    else:
        bounds = (0, 0, 1, 1)

    polygons = []
    for coords in polygons_raw:
        if len(coords) >= 3:
            normalized = _normalize_coords(coords, bounds)
            try:
                poly = Polygon(coords) if Polygon is not None else None
                area_ratio = (
                    poly.area / ((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]))
                    if poly is not None
                    else 0
                )
                if area_ratio > 0.001:
                    polygons.append(
                        {
                            "coordinates": normalized,
                            "type": "redline",
                            "area_ratio": area_ratio,
                        }
                    )
            except Exception:
                polygons.append({"coordinates": normalized, "type": "redline"})

    polygons.sort(key=lambda x: x.get("area_ratio", 0), reverse=True)
    return polygons, bounds


def _extract_pdf_polygons(file_path):
    """
    从 PDF 文件提取矢量轮廓（尽力而为，推荐优先使用 DXF）
    """
    if fitz is None:
        raise RuntimeError("服务器未安装 PyMuPDF / shapely，无法解析 PDF，请改用 DXF")

    doc = fitz.open(file_path)
    all_coords = []
    polygons_raw = []
    lines = []

    for page in doc:
        drawings = page.get_drawings()
        for drawing in drawings:
            path_coords = []
            for item in drawing["items"]:
                cmd = item[0]
                if cmd == "l":  # 直线
                    p1, p2 = item[1], item[2]
                    path_coords.extend([(p1.x, p1.y), (p2.x, p2.y)])
                elif cmd == "re":  # 矩形
                    rect = item[1]
                    rect_coords = [
                        (rect.x0, rect.y0),
                        (rect.x1, rect.y0),
                        (rect.x1, rect.y1),
                        (rect.x0, rect.y1),
                    ]
                    polygons_raw.append(rect_coords)
                elif cmd == "c":  # 三次贝塞尔（简化为端点）
                    p1, _, _, p4 = item[1], item[2], item[3], item[4]
                    path_coords.extend([(p1.x, p1.y), (p4.x, p4.y)])

            if path_coords:
                all_coords.extend(path_coords)
                if len(path_coords) >= 3:
                    first, last = path_coords[0], path_coords[-1]
                    dist = ((first[0] - last[0]) ** 2 + (first[1] - last[1]) ** 2) ** 0.5
                    if dist < 1:
                        polygons_raw.append(path_coords)
                    else:
                        lines.append(path_coords)

    doc.close()

    if lines and not polygons_raw and Polygon is not None:
        try:
            line_strings = [LineString(line) for line in lines if len(line) >= 2]
            merged = unary_union(line_strings)
            polys = list(polygonize(merged))
            for poly in polys:
                if poly.is_valid and poly.area > 0:
                    polygons_raw.append(list(poly.exterior.coords)[:-1])
        except Exception:
            pass

    if all_coords:
        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        bounds = (min(xs), min(ys), max(xs), max(ys))
    else:
        bounds = (0, 0, 1, 1)

    polygons = []
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y

    for coords in polygons_raw:
        if len(coords) >= 3 and width > 0 and height > 0:
            normalized = []
            for x, y in coords:
                nx = (x - min_x) / width
                ny = (y - min_y) / height
                normalized.append([nx, ny])
            try:
                poly = Polygon(coords) if Polygon is not None else None
                area_ratio = (
                    poly.area / (width * height) if (poly is not None and width * height > 0) else 0
                )
                if area_ratio > 0.001:
                    polygons.append(
                        {
                            "coordinates": normalized,
                            "type": "redline",
                            "area_ratio": area_ratio,
                        }
                    )
            except Exception:
                polygons.append({"coordinates": normalized, "type": "redline"})

    polygons.sort(key=lambda x: x.get("area_ratio", 0), reverse=True)
    return polygons, bounds


# 修改process_image_segmentation函数，支持多颜色类型
def process_image_segmentation(image_path):
    try:
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "图片读取失败"}
        
        original = img.copy()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_height, img_width = img.shape[:2]
        img_area = img_height * img_width
        
        # 定义颜色掩码
        masks = {}
        results = {}
        
        # -------- 紫色 --------
        lower_purple1 = np.array([120, 30, 30])
        upper_purple1 = np.array([160, 255, 255])
        lower_purple2 = np.array([160, 30, 30])
        upper_purple2 = np.array([180, 255, 255])
        purple_mask = cv2.bitwise_or(
            cv2.inRange(hsv, lower_purple1, upper_purple1),
            cv2.inRange(hsv, lower_purple2, upper_purple2)
        )
        masks["purple"] = purple_mask
        
        # -------- 绿色 --------
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        masks["green"] = green_mask
        
        # -------- 蓝色 --------
        lower_blue = np.array([90, 40, 40])
        upper_blue = np.array([125, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        masks["blue"] = blue_mask
        
        # -------- 粉色 --------
        lower_pink = np.array([155, 30, 80])
        upper_pink = np.array([180, 255, 255])
        pink_mask = cv2.inRange(hsv, lower_pink, upper_pink)
        masks["pink"] = pink_mask
        
        # 处理每种颜色
        for color_name, mask in masks.items():
            # 形态学处理
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
            mask = cv2.medianBlur(mask, 5)
            
            # 查找轮廓
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            color_contours = []
            
            # 处理每个轮廓
            for cnt in contours:
                area = cv2.contourArea(cnt)
                
                # 面积过滤
                if area < img_area * 0.001 or area > img_area * 0.5:
                    continue
                
                # 多边形近似
                epsilon = 0.005 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                if len(approx) < 3:
                    continue
                
                # 转换为相对坐标 (0-1范围)
                contour_points = approx.reshape(-1, 2).tolist()
                normalized_contour = []
                
                for x, y in contour_points:
                    # 归一化到0-1范围
                    nx = x / img_width
                    ny = y / img_height
                    normalized_contour.append([nx, ny])
                
                color_contours.append(normalized_contour)
            
            results[color_name] = color_contours
        
        return results
        
    except Exception as e:
        return {"error": str(e)}



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



# 保存地图截图
@app.route("/save-screenshot", methods=["POST"])
def save_screenshot():
    try:
        data = request.get_json(force=True)
        data_url = data.get("image")
        role = data.get("role", "").strip().lower()
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


#---------------------------------------------------------------------------------
#-----------------------------------AI分析相关-------------------------------------
#---------------------------------------------------------------------------------

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
   - 核心聚焦：提取群众对该片区城市更新的**具体有意义的建议**（而非情绪/描述）,优先覆盖城市更新核心方向；
   - 结构形式：用英文字母分点；
   - 内容要求：内容简明扼要，字数不得太多，内容不得重复，对城市更新意义不大的内容不必输出；
3. 输出要求：仅返回分点总结内容，无额外开场白/结束语。
        """.strip()  
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


# 技术经济指标数据库
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



# 街景图上传路由
@app.route("/upload-street-view", methods=["POST"])
def upload_street_view():
    try:
        # 获取上传的文件
        file = request.files.get('street_view')
        lng = request.form.get('lng')
        lat = request.form.get('lat')
        
        # 创建街景图保存目录
        street_view_dir = os.path.join(BASE_DIR, "static", "street_views")
        os.makedirs(street_view_dir, exist_ok=True)
        timestamp = int(time.time() * 1000)
        filename = f"street_view_{timestamp}_{lng}_{lat}.jpg"
        file_path = os.path.join(street_view_dir, filename)
        file.save(file_path)
        
        # 返回图片URL
        image_url = f"/static/street_views/{filename}"
        
        return jsonify({
            "ok": True, 
            "image_url": image_url,
            "message": "街景图上传成功"
        })
        
    except Exception as e:
        print(f"上传街景图时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# 街景图问题描述保存
@app.route('/save-problem-description', methods=['POST'])
def save_problem_description():
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        position = data.get('position')
        problem_description = data.get('problem_description')
        timestamp = data.get('timestamp')
        print(f"问题描述: {problem_description}")
        return jsonify({
            'ok': True,
            'message': '问题描述保存成功'
        })
    except Exception as e:
        print(f"保存问题描述失败: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        })

# 街景图分析路由
@app.route("/analyze-street-views", methods=["POST"])
def analyze_street_views():
    try:
        data = request.get_json(force=True) or {}
        analyses_data = data.get("analyses", [])
        STREET_IMAGE_DIR = os.path.join(BASE_DIR, "street_images")
        os.makedirs(STREET_IMAGE_DIR, exist_ok=True)
        results = []

        for i, analysis in enumerate(analyses_data):
            map_image_data = analysis.get("map_image_data")
            street_image_data = analysis.get("street_image_data")
            description = analysis.get("description", "")  
            position = analysis.get("position", {})
            
            try:
                # 保存地图截图
                timestamp = int(time.time() * 1000)
                map_image_filename = f"map_snapshot_{timestamp}_{i}.png"
                map_image_path = os.path.join(STREET_IMAGE_DIR, map_image_filename)
                _save_base64_image(map_image_data, map_image_path)

                # 保存街景图
                street_image_filename = f"street_view_{timestamp}_{i}.png"
                street_image_path = os.path.join(STREET_IMAGE_DIR, street_image_filename)
                
                # 检查是否是base64数据
                if street_image_data.startswith('data:image'):
                    _save_base64_image(street_image_data, street_image_path)
                else:
                    # 如果是文件路径，直接使用
                    if os.path.exists(street_image_data):
                        shutil.copy2(street_image_data, street_image_path)
                    else:
                        # 尝试从static目录查找
                        static_street_path = os.path.join(BASE_DIR, "static", "street_views", os.path.basename(street_image_data))
                        if os.path.exists(static_street_path):
                            shutil.copy2(static_street_path, street_image_path)
                        else:
                            raise ValueError(f"街景图文件不存在: {street_image_data}")

                # 街景图分析提示词设计
                prompt = f"""
请分析以下两张图片：
1. 图1是基地的整体卫星地图，红点标记的位置是街景图拍摄点（经纬度：{position.get('lng', '未知')}, {position.get('lat', '未知')}）。
2. 图2是该位置的街景图。

用户描述的具体问题：{description}

请根据街景图和用户描述的问题，给出专业、有针对性的分析报告。重点分析：
1. 问题产生的原因
2. 对城市规划的影响
3. 具体的改进建议

报告内容请控制在200字以内，确保分析专业且切中用户关心的问题。
                """.strip()

                # 调用qwenVLLM分析
                analysis_result = analyze_images([map_image_path, street_image_path], prompt)
                
                results.append({
                    "index": i,
                    "position": position,
                    "analysis": analysis_result,
                    "description": description,  
                    "map_image": map_image_filename,
                    "street_image": street_image_filename
                })

            except Exception as e:
                print(f"分析第{i+1}个街景图时发生错误: {e}")
                results.append({
                    "index": i,
                    "error": f"分析失败: {str(e)}"
                })

        return jsonify({
            "ok": True, 
            "results": results
        })

    except Exception as e:
        print(f"街景图分析时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


#AI分析重点路由
@app.route("/analyze-with-ai", methods=["POST"])
def analyze_with_ai():
    try:
        data = request.get_json(force=True) or {}
        style_suggestion = data.get("style_suggestion", "")
        survey_summary = data.get("survey_summary", "")  
        economic_indicators_str = data.get("economic_indicators_str", "")  
        street_view_analyses = data.get("street_view_analyses", [])
    
        big_path = os.path.join(SAVE_DIR, "big.png")
        small_path = os.path.join(SAVE_DIR, "small.png")
        standard_base_path = os.path.join(SAVE_DIR, "standard_base.png")

        # 构建核心分析框架
        sections = []
        
        # 1. 区位分析
        sections.append("""**一、区位格局分析**
基于图片1（区域卫星图），分析：
- 基地在区域发展轴线中的节点位置与战略价值
- 与周边重要功能区（商业/居住/产业/生态）的耦合关系
- 区域发展潜力评估与外部机遇识别""")
        
        # 2. 交通分析
        sections.append("""**二、交通系统诊断**
基于图片1和图片2（基地边界卫星图），重点分析：
- 外部交通网络可达性（主干道/轨道交通/慢行系统接口）
- 基地出入口合理性及与区域路网的衔接关系
- 内部交通微循环潜力与优化建议""")

        # 3. 建筑现状分析 - 整合经济指标与街景
        building_analysis = """**三、基地现状解读**
⚠️ **重要提示：图片2中的多边形闭合区域为规划基地边界，分析时必须严格限定在此范围内。图片3为基地三维实景，辅助理解建筑尺度。**

基于图片2（严格限定于多边形边界内）和图片3（三维建筑），分析：
- **空间肌理**：建筑布局模式（行列式/围合式/自由式）、街巷尺度与空间序列
- **建筑特征**：现状建筑高度分布、立面材质、结构形式与风貌品质
- **容量评估**：现状容积率、建筑密度与空间利用效率"""
        
        # 插入经济技术指标
        if economic_indicators_str:
            building_analysis += f"\n- **技术复核**：对照提供的技术指标「{economic_indicators_str}」验证现状建设的合规性与优化潜力"
        
        # 插入街景分析
        if street_view_analyses and len(street_view_analyses) > 0:
            street_insights = []
            for i, analysis in enumerate(street_view_analyses):
                if analysis.get('analysis') and not analysis.get('error'):
                    pos = analysis.get('position', {})
                    lng = round(pos.get('lng', 0), 6) if isinstance(pos.get('lng'), (int, float)) else '未知'
                    lat = round(pos.get('lat', 0), 6) if isinstance(pos.get('lat'), (int, float)) else '未知'
                    street_insights.append(f"街道采样点{i+1}[{lng},{lat}]：{analysis['analysis']}")
            
            if street_insights:
                building_analysis += f"\n- **实地校核**：结合街景调研发现「{'；'.join(street_insights)}」，评估人车环境真实体验与卫星图的差异"
        
        sections.append(building_analysis)

        # 4. 功能分区评估
        sections.append("""**四、功能布局评估**
综合三张图片，识别现状功能分布：
- 现状功能分区合理性（居住/商业/公共服务/绿地等边界清晰度）
- 功能混合度与活力分析，识别功能断层或错配区域
- 基于空间关系的功能重组建议与兼容性分析""")

        # 5. 群众需求
        if survey_summary:
            sections.append(f"""**五、需求适配策略**
基于群众调研报告「{survey_summary}」：
- 提炼核心诉求与空间痛点转化
- 设计民主化介入点与公众参与路径
- 平衡专业判断与民意需求的协商方案""")
        
        # 构建完整Prompt
        base_prompt = f"""你是一位具有20年经验的注册城乡规划师和一级建筑师，擅长基于多源遥感影像进行空间诊断。请严格按以下要求分析：

**图像识读规范**：
- 图片1：区域宏观卫星图（用于外部关系判断）
- 图片2：基地卫星图（含多边形边界线，⚠️严禁分析边界外区域）
- 图片3：基地三维建筑模型（用于体量与风貌感知）

{f'**设计价值取向**：在以上分析中，始终贯彻「{style_suggestion}」的设计理念，体现在空间结构、建筑风貌与场所营造策略中。' if style_suggestion else ''}

**分析框架**（请按此顺序输出，包含"现状诊断-关键问题-解决策略"三段式，字数不得太多，内容必须简明扼要）：

{chr(10).join(sections)}"""
        
        print("=== 最终生成的AI分析Prompt ===")
        print(base_prompt)
        print("=============================")
        
        analysis_result = analyze_images([big_path, small_path, standard_base_path], base_prompt)
        return jsonify({"ok": True, "analysis": analysis_result})
    
    except Exception as e:
        print(f"AI分析时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# 总结AI分析内容
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
1. 基于AI分析结果（下面会提供）生成用于AI图像生成工具的修改型prompt方案，需重点突出：
   - 建筑结构的显著调整（如布局、尺度、空间组织、与周围环境的互动）；
   - 建筑风格的明确变化；
   - 需要解决的问题以及解决方案；以及其他可能的总结点
   - 符合城市设计规划的基本逻辑；
2. 输出格式严格为：总结的prompt为：[你的生成内容]（仅保留此格式，无额外文字）。
3. 要求：语言简洁扼要、指令明确，仅用于修改基地相关图像；同时基于基地卫星地图（图片1）和基地三维地图（图片2）和提供的AI分析结果进行思考：【{analysis}】、；

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


#---------------------------------------------------------------------------------
#-----------------------------------草图生成相关-----------------------------------
#---------------------------------------------------------------------------------

#生成鸟瞰图以及视角转化图
@app.route("/generate-sketch", methods=["POST"])
def generate_sketch():
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt")
    pro = data.get("pro", False)
    big_path = os.path.join(SAVE_DIR, "big.png")
    small_path = os.path.join(SAVE_DIR, "small.png")
    standard_base_path = os.path.join(SAVE_DIR, "standard_base.png")
        
    # 鸟瞰图生成提示词
    complete_prompt = f"""**设计主题**：{prompt}

你是一名专业的城市规划设计师，生成一张**专业手绘风格三维规划草图**。

---

## 一、基地区域识别（核心规则）

**基地边界定义**：
- **图2多边形闭合区域 = 规划基地（核心区）**
- **设计重心100%在基地内**，建筑细节、空间结构、景观重点表现
- **基地外非设计对象**，但允许自然过渡与必要连接

---

## 二、三区域柔性分层（自然过渡）

### 核心区（图2多边形内）
- **设计深度最高**：建筑立面细节、屋顶层次、入口空间、连廊系统、庭院肌理
- 水彩/马克笔渲染，色彩饱和度适中，线稿清晰

### 过渡区（核心区外沿50-80米）
- **柔性缓冲带**，与核心区自然融合，**无硬边界**
- **允许内容**：
  - 延伸的道路系统（主次干道、步行道）
  - 简单的交通设施（公交站点、停车场入口）
  - 轻量景观（行道树轮廓、滨水岸线）
  - 必要的连接线（天桥、地下通道出入口）
- **表现形式**：色彩减淡30-50%，线稿简化，保持"设计未完成"的草图感

### 外围区（过渡区以外）
- **背景衬托层**，存在感极低
- **仅保留**：城市路网骨架（显示与基地的连通关系）、大型地标轮廓
- **表现形式**：极淡铅笔线/幽灵线，无色彩、无细节、无建筑体块

---

## 三、过渡自然性控制

- **边界消融**：核心区边缘色彩自然晕染至过渡区，避免切割感
- **连接优先**：强调基地与外部的道路衔接、视线通廊、空间渗透
- **层级递进**：设计完成度100%（核心）→ 60%（过渡）→ 10%（外围）
- **整体统一**：手绘质感一致，仅通过完成度区分层级

---

## 四、风格关键词

`architectural sketch`, `hand-drawn illustration`, `aerial perspective`, `soft tonal gradation`, `natural boundary transition`, `road network connection`, `site integration`, `watercolor wash`, `beige paper texture`, `pencil underdrawing`, `loose gestural strokes`, `contextual connection`, `layered design depth`

---

## 五、负面约束

`no hard boundary lines`, `no sudden color cutoff`, `no isolated core zone`, `no colored buildings outside transition zone`, `no detailed architecture in peripheral areas`, `no satellite texture`, `no black background`, `no text labels`, `no photorealistic rendering`

---

## 六、核查清单

☑ 核心区建筑细节丰富，设计完整  
☑ 过渡区自然衔接，道路与设施合理延伸  
☑ 外围区仅保留路网骨架，幽灵线处理  
☑ 三层级过渡柔和，无生硬边界  
☑ 米色纸张背景，手绘风格统一
☑ 无需标注参考图里的文字或者数字标注
"""

    try:
            # 调用banana生成鸟瞰图
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
            fname1 = f"bird_view_{timestamp}{pro_suffix}.png" 
            dst1 = os.path.join(GENERATED_DIR, fname1)
            if os.path.exists(source_path):
                if os.path.exists(dst1):
                    os.remove(dst1)
                shutil.move(source_path, dst1)
            image_url1 = f"/static/generated/{fname1}"
            
            # 生成平视图
            print("开始生成平视图...")
            ortho_prompt = """帮我生成图片：将基地平面图转为纯正视平视图，严禁鸟瞰俯视混合视角严禁标出刻度尺坐标轴标注。保持参考图所有建筑轮廓布局结构完全不变，在此基础上适当想象补充建筑正面立面细节门窗材质。镜头锁定：视线垂直于基地长边，位置贴临建筑红线正对长边中点，视高1.6米严格平视，等效50mm镜头，建筑正面线条绝对横平竖直画面底边与长边立面100%平行。空间分层：【基地内部】仅画面中心彩色标注区，建筑长边横向铺满画面90%宽度，立面从画面最下边缘直接起始零前景，想象补充正面门窗材质但保持原轮廓结构；【基地外部】仅限1-2层矮平房，仅画面左右极远端或正后方深处，0.1pt极细线框+95%透明度淡灰+高斯模糊，严禁遮挡基地立面。绝对禁止：刻度尺坐标轴任何标注，鸟瞰俯视混合视角，修改建筑轮廓结构，斜视三点透视，短边转向，前景道路广场人物，背景高楼。手绘水彩风格，纯正平视无标注，建筑轮廓100%忠于参考图正面细节合理想象补充。注意无需标注参考图里的文字或者数字标注。"""
            
            downloaded_paths, generated_filenames = doubao.generate([dst1], ortho_prompt)
            fname2 = f"flat_view_{timestamp}.png" 
            old_path = os.path.join(GENERATED_DIR, generated_filenames[0])
            new_path = os.path.join(GENERATED_DIR, fname2)
            if os.path.exists(old_path):
                if os.path.exists(new_path):
                    os.remove(new_path)
                shutil.move(old_path, new_path)
            image_url2 = f"/static/generated/{fname2}"
            print("平视图生成完成")
            
            # 生成顶视图
            print("开始生成俯视图...")
            top_view_prompt = """帮我生成图片： 你是一名精通建筑制图规范的城市规划设计师。你的唯一任务是将保利悦活荟基地参考图，进行纯粹的视角转换——生成从正上方90°垂直俯视的正交投影三维俯视图。 【绝对约束：零增删与100%保真原则】 转换过程仅涉及投影方式变更，严禁对原图内容进行任何取舍、简化、创造或风格化： 禁止删除任何建筑、构筑物、道路线段、景观元素 禁止新增任何原图不存在的元素 禁止合并或拆分原图中的任何轮廓 必须100%保留所有元素的轮廓、比例、相对位置及色彩属性，确保拓扑关系、材质表现与原图分毫不差 严禁主观改变原图中任何建筑元素的色彩、明暗或材质特征 【核心视角与投影指令】 观察点：固定于基地正上方，镜头光轴与地面绝对90°垂直 投影方式：严格正交投影，消除透视变形，所有水平线条保持平行且比例一致 画面定向：基地较长边必须与图片底边绝对平行，严禁任何旋转或倾斜 画面范围：完整包含原图所有内容，严禁裁切或重新构图 【纯粹视觉表现要求】 线条层级：手绘风格，通过线宽区分元素层级（建筑轮廓最粗、道路次之、景观最细），所有线条必须基于原图轮廓精准tracing 色彩处理：所有元素（尤其是建筑）的色彩必须与原始参考图保持完全一致，仅允许通过整体亮度-10%的方式对基地主体建筑范围进行视觉强调，使其与场地环境形成图底分离，但不得改变任何元素的色相、饱和度或材质质感 高度表达：通过统一方向轻微阴影体现建筑高度差异，但不得干扰平面轮廓清晰度 文字信息：严禁添加任何参考图里的文字和数字标注，保持图面纯粹。"""
            downloaded_paths, generated_filenames = doubao.generate([dst1], top_view_prompt)
            fname3 = f"top_view_{timestamp}.png"  
            old_path = os.path.join(GENERATED_DIR, generated_filenames[0])
            new_path = os.path.join(GENERATED_DIR, fname3)
            if os.path.exists(old_path):
                if os.path.exists(new_path):
                    os.remove(new_path)
                shutil.move(old_path, new_path)
            image_url3 = f"/static/generated/{fname3}"
            print("俯视图生成完成")
            
            # 返回不同视角的基地草图
            return jsonify({
                "ok": True, 
                "images": [image_url1, image_url2, image_url3],  
                "image_types": ["bird_view", "flat_view", "top_view"],  
                "filenames": [fname1, fname2, fname3],     
                "pro_version": pro
            })
                    
    except Exception as e:
            print(f"生成草图失败: {e}")
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"生成草图失败: {str(e)}"}), 500


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
现在你是具备城市设计规划专业能力的功能分区总结助手，请基于以下信息完成功能分区的修改方案总结：

【输入信息】
1. 参考图像：基地顶视图（small_over.png），展示基地的建筑结构体系
2. AI分析建议：最后会给你提供。

【任务要求】
请基于参考图像的基地建筑结构体系和AI分析建议，总结出具体的功能分区修改后的方案：

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
   - 语言简洁专业，聚焦功能分区方案，用总结性的结论概括，字数不得太多，语言简明扼要。
   - 无需提供任何其他内容如执行计划等，仅给出功能分区的修改方案即可
   - 注意参考调研报告分析的意见进行修改和总结：{analysis}
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


#生成功能分区平面图
@app.route("/generate-zoning-sketch", methods=["POST"])
def generate_zoning_sketch():
    try:
        # 获取前端数据
        data = request.get_json(force=True) or {}
        content_text = data.get("content_text")
        big_over_path = os.path.join(SAVE_DIR, "big_over.png")
        small_over_path = os.path.join(SAVE_DIR, "small_over.png")
        
        # 功能分区图提示词
        prompt = f"""**【功能分区方案】**
{content_text}

**角色**：建筑规划平面设计师，基于方案生成功能分区平面图。

**输入图像**：
- **图1**：基地及周边顶视图，仅参考宏观布局
- **图2**：基地顶视图，含多边形闭合边界（WORK_ZONE_LOCKED），**唯一功能分区绘制区域**

**核心指令**：

**Step 1: 边界锁定（绝对前提）**
- 精准识别图2多边形闭合边界 = WORK_ZONE_LOCKED（基地区域）
- **功能分区仅限此边界内，所有元素必须100%位于边界内**
- 边界模糊时**宁可缩小，不可扩大**

**Step 2: 内部分区（仅WORK_ZONE_LOCKED内）**
- **高饱和色块**：不同功能分区填充对比强烈的色彩（居住/商业/绿地等），色块紧贴边界
- **英文标注**：无衬线字体（RESIDENTIAL/COMMERCIAL/GREEN SPACE等），置于色块内或邻近区域
- **图例系统**：必须置于边界内空置角落（建议左下），含色块样本+英文名称对照
- **视角**：严格保持顶视平行投影

**Step 3: 外部处理（WORK_ZONE_LOCKED外）**
- **极简线条勾勒**：仅用简单手绘线条表示周边建筑轮廓，**无需渲染**（无色彩、无填充、无纹理）
- **绝对禁止**：
  - ❌ 任何功能分区或色块填充
  - ❌ 英文标注或文字
  - ❌ 黑色填充或深色覆盖

**风格**：城市规划草图手绘风，基地内色彩鲜明+英文标注+图例完整，基地外仅简单线条勾勒无渲染，边界过渡自然丝滑

**验证清单**：
☑ 所有功能分区、标注、图例均在WORK_ZONE_LOCKED内？
☑ 基地外无分区、无填充、无标注，仅简单线条勾勒？
☑ 禁止标注参考图里的文字地名
"""

        # 调用banana生成功能分区图
        image_paths = [big_over_path, small_over_path]
        banana.nanobanana_generate(prompt, image_paths, pro=False)
        generated_folder = GENERATED_DIR
        time.sleep(5)
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
                    "image_types": ["zoning"],  
                    "filenames": [fname]
                })
        else:
            return jsonify({"ok": False, "error": "未找到生成的图片"}), 500
                
    except Exception as e:
        print(f"生成功能分区图失败: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"功能分区图生成失败: {str(e)}"}), 500
    


# 生成流线图
@app.route("/generate-stream-map", methods=["POST"])
def generate_stream_map():
    try:
        data = request.get_json(force=True) or {}
        
        # 获取最新的鸟瞰图作为参考图
        generated_folder = GENERATED_DIR
        png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
        bird_view_files = [f for f in png_files if f.startswith('bird_view_')]
        bird_view_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
        
        if not bird_view_files:
            return jsonify({"ok": False, "error": "未找到鸟瞰图，请先生成鸟瞰图"}), 400
        
        latest_bird_view = os.path.join(generated_folder, bird_view_files[0])
        
        # 流线图提示词
        stream_prompt = """**基准图面**: 参照上传的彩色建筑群轴测图，理解人流流向绘制流线图。基地范围为画面中心彩色建筑群，外围无建筑细节的灰色体块为城市环境。 ## 视觉层级定义（关键优先级） **Layer 1 - 流线系统（绝对主导）**: 所有流线必须采用**超粗线宽（3.0pt+）**，全饱和色彩，100%不透明，在视觉上必须"压过"建筑底色。 **Layer 2 - 基地建筑（极度淡化）**: - 处理手法：**重度退晕（Heavy Ghosting）** - 饱和度降低至 **15-20%**（接近单色灰度），或叠加 **70%透明度白色蒙版** - 建筑仅保留**轮廓可识别性**（屋顶形式、体块关系），材质纹理、人物活动、细节设计全部虚化 - 目标：建筑成为"淡淡的底图-shadow"，确保3pt粗流线在上方形成**视觉悬浮感** **Layer 3 - 外部环境（极简轮廓）**: 外围灰色体块仅用**0.1pt极细线**勾勒，透明度**10%**，近乎隐形，仅作为空间参照系。 --- ## 流线绘制规范（全体系3.0pt超粗线） **主要内部流线（Primary Internal）**: - 线宽: **3.0pt 超粗实线** - 颜色: RGB(255, 87, 34) 荧光橙红，100%不透明，**零透明** - 路径: 中央广场 → 各建筑单元 → 次级庭院 - 箭头: 标准实心箭头（依附于线端，**禁止独立三角形符号**） **外部连接流线（External Interface）- 重点强化**: - 线宽: **3.0pt 超粗虚线**（与实线同宽，确保视觉权重平等） - 颜色: RGB(46, 204, 113) 荧光翠绿（高饱和度，与橙红形成补色对比） - 路径: **城市外部 → 穿透基地边界 → 连接内部主要流线** - 画法: 从画面边缘（城市道路）开始，用**超粗虚线**明确标示如何穿透基地边界，在入口处与橙红色实线**交汇融合**（merge at threshold） - 强调: **必须清晰展示外部人流如何"进入"基地**，流线在边界处不得中断 **次要流线（Secondary）**: - 线宽: **2.0pt 粗虚线**（仍保持较粗，不可过细） - 颜色: RGB(149, 165, 166) 灰蓝色（区别于外部绿色） - 路径: 屋顶平台、连廊轴线、垂直联系 --- ## 节点系统（严格控制数量） **城市-基地接口节点（Urban Interface Nodes）**: - **主入口**: 1个，**红色空心双圆环**（外径10mm，线宽2.5pt），位于外部绿线与内部橙红线**交汇点** - **次入口/穿透点**: 最多2个，**黄色空心圆环**（外径8mm），位于基地边界处 - **禁止**: 基地内部不得出现任何点状标记（包括广场、庭院、楼梯口） **垂直交通（极简符号）**: - **黑色实心小方块**（3x3mm）仅标注于流线转折处的建筑内部，**每栋楼不超过2个** - **禁止**: 禁止使用三角形、菱形、圆形作为楼梯符号；禁止在屋顶随意添加符号 --- ## 连接性设计强调（防AI遗漏） **外部-内部连续性要求**: - 绿色虚线（外部）必须在画面边缘就开始，**连续性延伸至基地内部**转为橙红实线，形成**"外部→入口→内部"的完整路径叙事** - 禁止流线在基地边界处"断裂"或"凭空出现" - 重点表现：**界面渗透性（Interface Permeability）** - 展示城市人流如何自然滑入基地内部 **图底关系强化**: - 建筑底色必须**足够淡**（建议RGB 240-245灰度系），确保**3pt的橙红与翠绿流线**在灰白背景上形成**霓虹灯管效应** - 流线必须**悬浮于建筑之上**（overlay），而非嵌入建筑材质中 --- ## 绝对禁止项（符号污染防控） - **NO TRIANGLES**: 全图禁止任何三角形符号（包括箭头、楼梯、装饰） - **NO RED DOTS**: 除1个主入口红色圆环外，禁止任何红色圆点、红点群 - **NO SCATTERED SYMBOLS**: 禁止在基地外围、道路、广场生成任何几何标记 - **NO BACKGROUND NOISE**: 基地外灰色体块内禁止流线、标注、填充色 - **NO THIN LINES**: 所有流线不得低于2.0pt，禁止细如发丝的线条 ## 最终效果描述 画面应呈现：**两条超粗的"光带"（橙红实线+翠绿虚线）在淡灰色的建筑幻影上交织**，翠绿光带从画面边缘穿透至中心，在入口处与橙红光带碰撞融合，形成强烈的城市连接叙事。建筑仅为淡淡的轮廓阴影，绝不与流线争抢视觉焦点。禁止标注参考图里的文字地名。"""

        # 调用doubao生成流线图
        downloaded_paths, generated_filenames = doubao.generate([latest_bird_view], stream_prompt)
        timestamp = int(time.time() * 1000)
        fname = f"stream_map_{timestamp}.png"
        old_path = os.path.join(GENERATED_DIR, generated_filenames[0])
        new_path = os.path.join(GENERATED_DIR, fname)
        
        if os.path.exists(old_path):
            if os.path.exists(new_path):
                os.remove(new_path)
            shutil.move(old_path, new_path)
        
        image_url = f"/static/generated/{fname}"
        
        return jsonify({
            "ok": True, 
            "images": [image_url],  
            "image_types": ["stream_map"],
            "filenames": [fname]
        })
                
    except Exception as e:
        print(f"生成流线图失败: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"流线图生成失败: {str(e)}"}), 500


#生成实景效果图
@app.route("/generate-effect-image", methods=["POST"])
def generate_effect_image():
    try:
        
        # 效果图提示词
        effect_prompt = f"""
核心任务
将基地鸟瞰图转换为基地外部广场人视实景效果图，人站在城市公共空间（广场/街道/绿地）向基地内观望，展现参考图中的建筑群整体风貌与建筑结构。
视角规范（关键）
观察位置：人站立于基地红线内的室外广场、街道或开放绿地，背向或侧向基地边界，面向基地内部建筑群
视线方向：由外向内水平环顾或微仰，捕捉多栋建筑的外部体量关系、立面组合与空间围合
视线高度：人眼高度（1.6-1.8米），城市街道真实视角
构图原则：广场铺地/街道占据前景，人群穿插中景，建筑群落作为画面主体占据中后景，形成"人在广场看建筑"的层次
建筑结构表现（严格依据参考图）
群体关系：忠实还原参考图中多栋建筑的布局关系、围合方式、高低错落
结构可视化：建筑外立面结构体系（框架、悬挑、退台、连廊、立体交通）清晰可见
空间尺度：准确表达广场开敞感与建筑围合度的比例关系，非室内封闭感
场景氛围营造
人群活动：广场/街道上有行人漫步、停留、聚集，呈现城市公共空间的活力
商业暗示：底层可见商铺骑楼、橱窗、招牌，但建筑主体保持外部体量完整性，不暴露室内
环境要素：广场家具、绿化景观、地面铺装、城市家具丰富场景，强化"室外"属性
视觉品质标准
光影系统：自然天光主导，建筑外立面真实投影与材质反射，ray tracing级光照
材质真实度：石材/砖墙面、玻璃幕墙、金属屋面、混凝土肌理、广场铺装达到照片级
氛围营造：开放空间的空气透视、城市噪音感、人流穿梭的动势、建筑与天空的关系
细节精度：立面构造节点、门窗划分、材质分缝、人群动态清晰可见
技术参数
分辨率：8K超高清
景深控制：f/8-f/11光圈，建筑群整体清晰，广场前景适度细节
光学模拟：ISO 100，消除畸变，还原人眼真实视野
严格禁止项（关键）
❌ 人位于任何建筑室内空间（商场中庭、走廊、店铺、门厅）
❌ 画面呈现建筑内部空间、室内吊顶、室内照明
❌ 建筑结构与参考图布局不符（私自改变建筑位置、增减栋数、改变围合关系）
❌ 画面出现基地外部环境（基地外城市道路、周边无关建筑、基地外城市景观）
❌ 过度仰视导致天空占比过大，丧失广场视角的平视感
❌ 标注参考图里的文字地名

"""

        # 寻找最新的鸟瞰图作为参考
        generated_folder = GENERATED_DIR
        png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
        bird_view_files = [f for f in png_files if f.startswith('bird_view_')]
        bird_view_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
        if not bird_view_files:
            return jsonify({"ok": False, "error": "未找到鸟瞰图，请先生成鸟瞰图"}), 400
        latest_bird_view = os.path.join(generated_folder, bird_view_files[0])
        image_paths = [latest_bird_view]

        #调用banana生成效果图
        banana.nanobanana_generate(effect_prompt, image_paths, pro=False)
        time.sleep(5)
        png_files = [f for f in os.listdir(generated_folder) if f.endswith('.png')]
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join(generated_folder, x)), reverse=True)
        
        if png_files:
            latest_file = png_files[0]
            source_path = os.path.join(generated_folder, latest_file)
            timestamp = int(time.time() * 1000)
            fname = f"effect_view_{timestamp}.png"
            dst = os.path.join(GENERATED_DIR, fname)
            
            if os.path.exists(source_path):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(source_path, dst)
                image_url = f"/static/generated/{fname}"
                
                return jsonify({
                    "ok": True, 
                    "images": [image_url],  
                    "image_types": ["effect_view"],
                    "filenames": [fname]
                })
        else:
            return jsonify({"ok": False, "error": "未找到生成的图片"}), 500
                
    except Exception as e:
        print(f"生成效果图失败: {e}")
        traceback.print_exc()
      
      

#---------------------------------------------------------------------------------
#-----------------------------------修改草图相关（维修中）-----------------------------------
#---------------------------------------------------------------------------------

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
    


@app.route("/parse-cad", methods=["POST"])
def parse_cad():
    """
    解析 CAD/PDF 文件接口
    请求体:
        file: base64编码的文件内容（data:…;base64,xxx）
        filename: 文件名（用于判断格式）
        layer_filter: 可选，图层过滤关键词列表
    返回:
        ok: 是否成功
        polygons: 多边形列表，每个包含归一化坐标
        bounds: 原始边界
        file_type: DXF / PDF
    """
    try:
        data = request.get_json() or {}
        file_data = data.get("file", "")
        filename = data.get("filename", "unknown.dxf")
        layer_filter = data.get("layer_filter")

        if not file_data:
            return jsonify({"ok": False, "error": "缺少文件数据"}), 400

        if "," in file_data:
            file_data = file_data.split(",", 1)[1]

        file_bytes = base64.b64decode(file_data)

        ext = os.path.splitext(filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            if ext == ".dxf":
                polygons, bounds = _extract_dxf_polygons(tmp_path, layer_filter)
                file_type = "DXF"
            elif ext == ".pdf":
                polygons, bounds = _extract_pdf_polygons(tmp_path)
                file_type = "PDF"
            elif ext == ".dwg":
                return jsonify(
                    {
                        "ok": False,
                        "error": "DWG 格式暂不支持直接解析，请在 CAD 软件中另存为 DXF 后上传",
                    }
                )
            else:
                return jsonify(
                    {"ok": False, "error": f"不支持的文件格式: {ext}，请上传 DXF 或 PDF"}
                )

            if not polygons:
                return jsonify(
                    {
                        "ok": False,
                        "error": "未能从文件中提取到有效的多边形轮廓，请确保文件包含闭合的红线图形",
                    }
                )

            return jsonify(
                {
                    "ok": True,
                    "polygons": polygons,
                    "bounds": bounds,
                    "file_type": file_type,
                    "message": f"成功从 {file_type} 文件中提取到 {len(polygons)} 个轮廓",
                }
            )
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        print("解析 CAD/PDF 文件失败:", e)
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"解析失败: {str(e)}"}), 500

@app.route("/save-selection", methods=["POST"])
def save_selection():
    try:
        data = request.get_json()
        selections = data.get("selections", [])
        
        if not selections:
            return jsonify({"ok": False, "error": "没有选择数据"}), 400
        
        # 创建保存目录
        selection_dir = os.path.join(BASE_DIR, "selections")
        os.makedirs(selection_dir, exist_ok=True)
        
        # 保存为JSON文件
        timestamp = int(time.time())
        filename = f"selection_{timestamp}.json"
        filepath = os.path.join(selection_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "selectionCount": len(selections),
                "selections": selections
            }, f, ensure_ascii=False, indent=2)
        
        # 可选：保存为DXF文件
        try:
            from ezdxf import new
            from ezdxf.math import Vec2
            
            doc = new('R2010')
            msp = doc.modelspace()
            
            for selection in selections:
                # 这里需要将地理坐标转换为合适的坐标系
                # 简化处理：直接使用原坐标
                points = [Vec2(coord[0], coord[1]) for coord in selection["coordinates"]]
                msp.add_lwpolyline(points, format='xy', close=True)
            
            dxf_path = os.path.join(selection_dir, f"selection_{timestamp}.dxf")
            doc.saveas(dxf_path)
            
        except ImportError:
            print("ezdxf未安装，跳过DXF导出")
        
        return jsonify({
            "ok": True,
            "message": f"成功保存 {len(selections)} 个选区",
            "filename": filename,
            "selectionCount": len(selections)
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 轮廓处理路由（已存在，无需新增）
@app.route("/process-contour", methods=["POST"])
def process_contour():
    try:
        data = request.get_json()
        data_url = data.get("image")
        selection_rect = data.get("selectionRect", {})  # 接收 selectionRect
        
        if not data_url:
            return jsonify({"ok": False, "error": "没有图片数据"}), 400
        
        # 解码base64图片
        header, b64 = data_url.split(",", 1)
        image_data = base64.b64decode(b64) if "base64" in header else b64.encode("utf-8")
        
        # 保存截图用于调试
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_file.write(image_data)
        temp_file.close()
        
        # 保存到特定目录以便查看
        debug_dir = os.path.join(BASE_DIR, "debug_images")
        os.makedirs(debug_dir, exist_ok=True)
        import time
        debug_filename = f"debug_{int(time.time())}.png"
        debug_path = os.path.join(debug_dir, debug_filename)
        shutil.copy2(temp_file.name, debug_path)
        
        print(f"💾 调试图片已保存到: {debug_path}")
        
        # 处理图像
        result = process_image_segmentation(temp_file.name)
        
        # 清理临时文件
        os.unlink(temp_file.name)
        
        print(f"🔍 检测结果: {result}")
        
        if "error" in result:
            return jsonify({"ok": False, "error": result["error"]}), 500
        
        # 返回结构化数据
        polygons = []
        
        # 处理各种颜色的轮廓（和前端保持一致）
        color_types = {
            "purple": "purple",
            "green": "green", 
            "blue": "blue",
            "pink": "pink"
        }
        
        for color_name, color_type in color_types.items():
            if color_name in result and result[color_name]:
                for i, contour in enumerate(result[color_name]):
                    polygons.append({
                        "id": f"{color_name}_{i}",
                        "type": color_type,
                        "coordinates": contour,  # 像素坐标
                        "contour": contour  # 兼容前端代码
                    })
        
        return jsonify({
            "ok": True,
            "message": f"成功提取 {len(polygons)} 个轮廓",
            "polygons": polygons,
            "selectionRect": selection_rect  # 原样返回给前端
            
        })
        
    except Exception as e:
        print(f"处理轮廓时发生错误: {e}")
        traceback.print_exc()
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