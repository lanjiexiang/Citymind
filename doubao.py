from playwright.sync_api import sync_playwright
import pathlib
import time
import os
import base64
import re
from urllib.parse import urlparse, unquote
from PIL import Image

# 用于持久化浏览器登陆信息
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "doubao_profile")

# 图片保存目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "static", "generated")  

#下载图片函数
def download_image_to_generated(page, src: str) -> str:
    os.makedirs(GENERATED_DIR, exist_ok=True)
    try:
        resp = page.request.get(src, timeout=60000)
        if resp.status != 200:
            raise RuntimeError(f"下载失败，HTTP status={resp.status}")
        body = resp.body()
        timestamp = int(time.time() * 1000)
        fname = f"generated_{timestamp}.png"
        target = os.path.join(GENERATED_DIR, fname)
        with open(target, "wb") as f:
            f.write(body)
        return target
        
    except Exception as e:
        print(f"下载图片失败: {e}")
        raise

# 豆包生图爬虫主函数
def generate(image_paths, prompt_text: str) -> list[str]:

    if isinstance(image_paths, str):
        image_paths = [image_paths]  
    downloaded_paths = []
    generated_filenames = []
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()

        # 修改点：优化登录状态判断逻辑
        page.goto("https://www.doubao.com/chat/", wait_until="domcontentloaded")
        try:
            # 明确等待登录按钮出现（超时10秒），如果按钮可见则表示未登录
            page.wait_for_selector("[data-testid='to_login_button']", timeout=10000)
            print("检测到未登录状态，执行登录流程...")
            page.get_by_test_id("to_login_button").click()
            page.get_by_test_id("login_third_aweme_v2").click()
            page.get_by_test_id("login_privacy_dialog_confirm_button").click()
            print("登录流程完成")
        except Exception as e:
            # 如果等待超时或按钮不可见，则认为已登录
            print("未检测到登录按钮，可能已登录，跳过登录步骤")

        # 进入 AI 创作页面
        page.locator("a[href='/chat/create-image']").click()
        print("进入 AI 创作页面…")
        drop_selector = "div.editor-container-FvjPyp[data-testid='skill-modal-image-creation']"
        page.wait_for_selector(drop_selector, timeout=30000)

        # 上传参考图片
        file_paths_resolved = []
        for path in image_paths:
            file_path_obj = pathlib.Path(path).resolve()
            if not file_path_obj.exists():
                raise FileNotFoundError(f"文件不存在: {file_path_obj}")
            file_paths_resolved.append(str(file_path_obj))
        inputs = page.locator("input[type=file]")
        inputs.nth(0).set_input_files(file_paths_resolved)
        page.wait_for_timeout(1500)

        # 提示词框输入
        editor_selector = "div.editor-A1E_5W div[role='textbox'][data-testid='chat_input_input']"
        page.wait_for_selector(editor_selector, timeout=10000)
        page.click(editor_selector)
        time.sleep(0.2)
        page.keyboard.type(prompt_text, delay=60)
        print(f"已输入 prompt: {prompt_text}")
        page.get_by_test_id("chat_input_send_button").click()
        print("已点击发送按钮。")

        # 监视生成的图片元素
        target_selector = "img.image-Q7dBqW"
        time.sleep(3)
        downloaded_paths = []
        generated_filenames = []
        page.wait_for_selector(target_selector, timeout=0) 
        elems = page.locator(target_selector)
        count = elems.count()
        if count > 0:
            print(f"检测到图片元素，等待图片完全加载...")
            page.wait_for_timeout(5000)                
            img_el = elems.nth(0)

            try:
                src = img_el.get_attribute("src")
                is_complete = img_el.evaluate("(img) => img.complete && img.naturalWidth > 0")
                
                # 打开预览窗口
                img_el.click()
                page.wait_for_timeout(3000)
                
                # 查找预览窗口中的高清图片
                preview_selector = "img[data-testid='in_painting_picture']"
                preview_imgs = page.locator(preview_selector)
                preview_img = preview_imgs.nth(0)
                preview_src = preview_img.get_attribute("src")
                if preview_src:
                    downloaded_path = download_image_to_generated(page, preview_src)
                    downloaded_paths.append(downloaded_path)
                    filename = os.path.basename(downloaded_path)
                    generated_filenames.append(filename)
                    print(f"高清原图已保存: {downloaded_path}")
              
            except Exception as e:
                print(f"处理图片时出错: {e}")
                raise

        context.close()
        return downloaded_paths, generated_filenames