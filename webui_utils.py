import os
import streamlit as st
import shutil
import glob
from pathlib import Path
from PIL import Image
import imagehash
from collections import defaultdict
import random
import tkinter as tk
from tkinter import filedialog

# --- 目录选择器组件 ---
def st_directory_selector(st_placeholder, key="dir_selector", initial_path="."):
    """
    一个简单的基于Streamlit的目录选择器，支持系统原生对话框。
    """
    if key not in st.session_state:
        st.session_state[key] = os.path.abspath(initial_path)
    
    # 用于强制重新渲染的计数器
    if f"{key}_refresh_counter" not in st.session_state:
        st.session_state[f"{key}_refresh_counter"] = 0

    # 布局: [浏览按钮] [路径输入框]
    col1, col2 = st_placeholder.columns([1.5, 8.5])
    
    with col1:
        if st.button("📂 浏览...", key=f"btn_browse_{key}", help="打开系统文件浏览器选择文件夹"):
            try:
                root = tk.Tk()
                root.withdraw() # 隐藏主窗口
                root.wm_attributes('-topmost', 1) # 窗口置顶
                
                # 优先使用当前已选路径作为起始路径
                start_dir = st.session_state[key]
                if not os.path.exists(start_dir):
                    start_dir = os.path.abspath(".")
                
                selected_path = filedialog.askdirectory(initialdir=start_dir, title="选择文件夹")
                root.destroy()
                
                if selected_path:
                    abs_path = os.path.abspath(selected_path)
                    st.session_state[key] = abs_path
                    # 增加计数器强制重新渲染
                    st.session_state[f"{key}_refresh_counter"] += 1
                    st.rerun()
            except Exception as e:
                st.error(f"无法打开系统选择框: {e}")

    with col2:
        current_val = st.session_state[key]
        # 使用 on_change 回调确保输入框的回车也能触发状态更新
        def update_path():
            new_path = st.session_state[f"input_{key}"]
            if os.path.isdir(new_path):
                st.session_state[key] = os.path.abspath(new_path)
                # 增加计数器强制重新渲染
                st.session_state[f"{key}_refresh_counter"] += 1
            else:
                st.toast("⚠️ 路径不存在", icon="❌")

        # 使用计数器作为key的一部分来强制重新渲染
        unique_key = f"input_{key}_{st.session_state[f'{key}_refresh_counter']}"
        st.text_input(
            "路径", 
            value=current_val, 
            key=unique_key, 
            label_visibility="collapsed",
            on_change=update_path 
        )

    return st.session_state[key]

import base64
import streamlit.components.v1 as components

def get_file_info(file_path):
    """获取文件大小字符串和分辨率"""
    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes/1024:.1f} KB"
        else:
            size_str = f"{size_bytes/(1024*1024):.2f} MB"
            
        with Image.open(file_path) as img:
            resolution = f"{img.width} x {img.height}"
            
        return size_str, resolution
    except Exception as e:
        return "Unknown", "Unknown"

def st_zoomable_image(image_path, height=600):
    """
    创建一个支持滚轮缩放和拖拽的图片组件
    """
    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        b64_img = base64.b64encode(img_bytes).decode()
        
        # HTML/JS 代码
        html_code = f"""
        <style>
            .container {{
                width: 100%;
                height: {height}px;
                overflow: hidden;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f0f2f6;
                position: relative;
                display: flex;
                justify-content: center;
                align-items: center;
                cursor: grab;
            }}
            .container:active {{
                cursor: grabbing;
            }}
            img {{
                max-width: 100%;
                max-height: 100%;
                transition: transform 0.1s ease-out;
                user-select: none;
                -webkit-user-drag: none;
                transform-origin: center center;
            }}
        </style>
        <div class="container" id="zoom-container">
            <img src="data:image/png;base64,{b64_img}" id="zoom-img">
        </div>
        <script>
            const container = document.getElementById('zoom-container');
            const img = document.getElementById('zoom-img');
            
            let scale = 1;
            let themeScale = 1; // 基础适配缩放
            let panning = false;
            let pointX = 0;
            let pointY = 0;
            let startX = 0;
            let startY = 0;

            // 滚轮缩放
            container.addEventListener('wheel', (e) => {{
                e.preventDefault();
                const xs = (e.clientX - pointX) / scale;
                const ys = (e.clientY - pointY) / scale;
                
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                let newScale = scale * delta;
                
                // 限制缩放范围
                if (newScale < 0.1) newScale = 0.1;
                if (newScale > 10) newScale = 10;
                
                scale = newScale;
                
                // 保持鼠标指向的位置不变
                // (简单版：暂时不做复杂的中心点计算，直接缩放)
                setTransform();
            }});

            // 拖拽
            container.addEventListener('mousedown', (e) => {{
                e.preventDefault();
                startX = e.clientX - pointX;
                startY = e.clientY - pointY;
                panning = true;
            }});

            container.addEventListener('mouseup', (e) => {{
                panning = false;
            }});
            
            container.addEventListener('mouseleave', (e) => {{
                panning = false;
            }});

            container.addEventListener('mousemove', (e) => {{
                e.preventDefault();
                if (!panning) return;
                pointX = e.clientX - startX;
                pointY = e.clientY - startY;
                setTransform();
            }});

            function setTransform() {{
                img.style.transform = `translate(${{pointX}}px, ${{pointY}}px) scale(${{scale}})`;
            }}
            
            // 简单重置双击
            container.addEventListener('dblclick', () => {{
                scale = 1;
                pointX = 0;
                pointY = 0;
                setTransform();
            }});
        </script>
        """
        components.html(html_code, height=height + 10)
    except Exception as e:
        st.error(f"加载图片组件失败: {e}")


# --- 常量 ---
PROTECTED_FILES = {
    'requirements.txt', 
    'README.md', 
    'LICENSE', 
    'README.txt',
    'prompts.txt',
    'config.txt'
}

# --- 功能逻辑重写/封装 ---

def delete_unmatched_txt_files_func(folder_path):
    """
    删除没有对应图片的txt文件 (来自 delete_useless_txt.py 的逻辑)
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return 0, f"错误: 该路径不存在或不是文件夹"
    
    deleted_count = 0
    logs = []

    for filename in os.listdir(folder_path):
        if filename in PROTECTED_FILES:
            continue
            
        if filename.lower().endswith('.txt'):
            base_name = os.path.splitext(filename)[0]
            txt_file_path = os.path.join(folder_path, filename)
            has_matching_image = False
            for ext in image_extensions:
                image_path = os.path.join(folder_path, f"{base_name}{ext}")
                if os.path.exists(image_path) and os.path.isfile(image_path):
                    has_matching_image = True
                    break
            if not has_matching_image:
                try:
                    os.remove(txt_file_path)
                    logs.append(f"已删除: {filename}")
                    deleted_count += 1
                except Exception as e:
                    logs.append(f"删除失败 {filename}: {str(e)}")
    
    return deleted_count, logs

def get_image_phash(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except Exception as e:
        return None

def get_image_resolution(image_path):
    try:
        with Image.open(image_path) as img:
            return img.width * img.height
    except Exception as e:
        return 0

def find_duplicate_images(directory, threshold=5):
    """
    查找重复图片 (来自 hash_to_delete.py)
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    image_hashes = {}
    
    if not os.path.exists(directory):
        return []
        
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in image_extensions and os.path.isfile(file_path):
            phash = get_image_phash(file_path)
            if phash:
                image_hashes[file_path] = phash
    
    groups = []
    processed = set()
    
    keys = list(image_hashes.keys())
    for i, path1 in enumerate(keys):
        if path1 in processed:
            continue
        
        hash1 = image_hashes[path1]
        group = [path1]
        processed.add(path1)
        
        for path2 in keys[i+1:]:
            if path2 not in processed:
                hash2 = image_hashes[path2]
                if hash1 - hash2 <= threshold:
                    group.append(path2)
                    processed.add(path2)
        
        if len(group) > 1:
            groups.append(group)
            
    return groups

def process_duplicate_groups(groups, method, delete_txt=False):
    """
    处理重复图片组
    method: 'manual' (仅返回列表供展示), 'auto_no_txt' (自动删除无txt的), 'auto_all' (自动删除)
    """
    results = []
    deleted_count = 0
    
    for group in groups:
        # 分析组内情况
        details = []
        for file_path in group:
            txt_path = os.path.splitext(file_path)[0] + '.txt'
            has_txt = os.path.exists(txt_path)
            res = get_image_resolution(file_path)
            details.append({
                'path': file_path,
                'has_txt': has_txt,
                'txt_path': txt_path if has_txt else None,
                'resolution': res
            })
        
        # 按照分辨率降序排序
        details.sort(key=lambda x: x['resolution'], reverse=True)
        
        if method == 'manual':
            results.append({'group': details, 'action': 'manual'})
            continue
        
        to_keep = details[0] # 默认保留分辨率最高的
        to_delete = details[1:]
        
        # 如果策略是只删除无TXT的
        if method == 'auto_no_txt':
            # 只有当存在带TXT的文件时，才敢放心删除无TXT的
            has_txt_files = [d for d in details if d['has_txt']]
            no_txt_files = [d for d in details if not d['has_txt']]
            
            if has_txt_files:
                to_delete = no_txt_files # 只删除无TXT的
            else:
                # 都是无TXT的，保留最高分辨率
                pass 
                
        # 执行删除
        for item in to_delete:
            try:
                os.remove(item['path'])
                deleted_count += 1
                log_msg = f"删除了: {os.path.basename(item['path'])}"
                if delete_txt and item['has_txt']:
                    os.remove(item['txt_path'])
                    log_msg += " (及TXT)"
                results.append(log_msg)
            except Exception as e:
                results.append(f"删除失败 {os.path.basename(item['path'])}: {str(e)}")
                
    return results

def get_image_files(folder_path):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    files = []
    if os.path.isdir(folder_path):
        for f in os.listdir(folder_path):
            if os.path.splitext(f)[1].lower() in image_extensions:
                files.append(os.path.join(folder_path, f))
    return sorted(files)

def get_txt_content(image_path):
    txt_path = os.path.splitext(image_path)[0] + ".txt"
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read(), txt_path
        except:
            return "", txt_path
    return "", txt_path

def save_txt_content(txt_path, content):
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except:
        return False
