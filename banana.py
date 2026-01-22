# -*- coding: utf-8 -*-
import os
import time
import base64
from playwright.sync_api import sync_playwright

#图片保存目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "static", "generated")  

#nano banana生图主函数
def nanobanana_generate(prompt_text, image_paths, pro=False):

    script_dir = BASE_DIR
    generated_folder = GENERATED_DIR
    
    # 定义profile文件夹路径
    profile_folder = os.path.join(script_dir, "banana_profile")
    storage_state_path = os.path.join(profile_folder, "storage_state.json")
        
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        # 检查是否存在cookies
        if os.path.exists(storage_state_path):
            print("检测到已保存的登录状态，尝试使用...")
            context = browser.new_context(storage_state=storage_state_path)
            page = context.new_page()
            page.goto("https://nano.zhihuiapi.top/")
            
            # 等待页面加载
            page.wait_for_timeout(5000)
            
            # 检查迁移广告关闭按钮
            migration_ad_close = page.locator('button.migration-ad-close')
            if migration_ad_close.is_visible():
                print("检测到迁移广告关闭按钮，正在点击...")
                migration_ad_close.click()
                page.wait_for_timeout(1000)
                print("迁移广告已关闭")
            else:
                print("未检测到迁移广告关闭按钮")
            
            # 检查登录按钮是否存在（判断是否需要重新登录）
            login_button = page.locator('button.btn.btn-secondary:has-text("登录")')
            if login_button.is_visible():
                print("检测到登录按钮，说明需要重新登录...")
                # 关闭当前context，重新创建不带cookies的context
                context.close()
                context = browser.new_context()
                page = context.new_page()
                page.goto("https://nano.zhihuiapi.top/")
                print("重新加载页面完成")
                
                # 执行登录流程
                need_login = True
            else:
                print("未检测到登录按钮，使用已保存的登录状态继续操作")
                need_login = False
        else:
            print("未找到登录状态，开始执行登录流程...")
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://nano.zhihuiapi.top/")
            print("网页加载完成")
            need_login = True
        
        # 如果需要登录，执行登录流程
        if need_login:
            # 检查迁移广告关闭按钮
            page.wait_for_timeout(2000)
            migration_ad_close = page.locator('button.migration-ad-close')
            if migration_ad_close.is_visible():
                print("检测到迁移广告关闭按钮，正在点击...")
                migration_ad_close.click()
                page.wait_for_timeout(1000)
                print("迁移广告已关闭")
            else:
                print("未检测到迁移广告关闭按钮")
            
            # 点击登录按钮
            login_button = page.locator('button.btn.btn-secondary:has-text("登录")')
            if login_button.is_visible():
                print("检测到登录按钮，正在点击...")
                login_button.click()
                page.wait_for_timeout(1000)
            else:
                print("未检测到登录按钮，请检查页面状态")
                return
                
            # 输入用户名
            username_input = page.locator('input[type="text"].form-input[placeholder="请输入您的用户名"]')
            username_input.wait_for(state="visible")
            username_input.fill("fdublue")
            page.wait_for_timeout(500)
                
            # 输入密码
            password_input = page.locator('input[type="password"].form-input[placeholder="请输入密码"]')
            password_input.fill("L19980908l!")
            page.wait_for_timeout(500)
                
            # 点击登录提交按钮
            submit_button = page.locator('button.auth-btn:has-text("登录")')
            submit_button.click()
            page.wait_for_timeout(3000)

            # 创建profile文件夹并保存登录状态
            if not os.path.exists(profile_folder):
                os.makedirs(profile_folder)
                print(f"已创建文件夹: {profile_folder}")
            context.storage_state(path=storage_state_path)
            print(f"登录状态已保存到: {storage_state_path}")

        # 点击16:9比例按钮
        page.wait_for_timeout(2000)
        aspect_ratio_button = page.locator('button.aspect-ratio-btn:has-text("16:9")')
        aspect_ratio_button.wait_for(state="visible", timeout=10000)
        aspect_ratio_button.click()
        page.wait_for_timeout(1000)
        
        # 如果pro参数为True，点击Banana Pro按钮
        if pro:
            pro_button = page.locator('button.model-tab .tab-text:has-text("Banana Pro")')
            pro_button.wait_for(state="visible", timeout=10000)
            pro_button.click()
            page.wait_for_timeout(1000)
        
        # 按顺序上传每个图片
        upload_area = page.locator('div.upload-area')
        for i, image_path in enumerate(image_paths, 1):
            print(f"正在上传第 {i} 个图片: {os.path.basename(image_path)}")
            file_input = page.locator('input[type="file"]#image-upload')
            file_input.set_input_files(image_path)
            page.wait_for_timeout(2000)
            print(f"第 {i} 张图片上传完成")
        
        # 输入提示词
        prompt_input = page.locator('textarea.prompt-input')
        prompt_input.wait_for(state="visible", timeout=10000)
        prompt_input.fill("")
        prompt_input.fill(prompt_text)

        # 上传任务
        process_button = page.locator('button.process-btn')
        process_button.wait_for(state="visible", timeout=10000)
        process_button.click()
        
        # 监测结果图片容器并等待图片生成
        image_updated = False
        last_src = ""
        while not image_updated:
            result_container = page.locator('div.result-image-container img')
            if result_container.count() > 0:
                current_src = result_container.get_attribute('src') or ""
                
                # 检查src是否更新且包含base64数据
                if current_src and current_src.startswith('data:image') and current_src != last_src:
                    print("检测到图片已更新！")
                    image_updated = True
                    
                    # 下载图片
                    base64_data = current_src.split(',')[1]
                    timestamp = int(time.time())
                    pro_suffix = "_pro" if pro else ""
                    output_path = os.path.join(generated_folder, f"generated_image{pro_suffix}_{timestamp}.png")
                    with open(output_path, 'wb') as f:
                        f.write(base64.b64decode(base64_data))
                last_src = current_src
        
        # 关闭浏览器
        context.close()
        browser.close()