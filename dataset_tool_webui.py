import streamlit as st
import os
import sys
import asyncio
import time
import io
import contextlib
import shutil
from PIL import Image

# 添加当前路径到 path 以便 import 本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入工具模块
try:
    from webui_utils import (
        st_directory_selector, 
        delete_unmatched_txt_files_func, 
        find_duplicate_images, 
        process_duplicate_groups, 
        get_image_files, 
        get_txt_content, 
        save_txt_content,
        get_file_info,
        st_zoomable_image
    )
    import add_prefix
    import check_matches
    import drop_tag
    import fill_img
    import ganther_children_folders_to_one_folder as merge_folders
    import downloader_for_lora_train as downloader
    import saucenao
    from tagger_api import TaggerAPIClient
    # ComfyUI Imports
    try:
        from comfy_api_backup.comfy_library.client import ComfyUIClient
        from comfy_api_backup.comfy_library.workflow import ComfyWorkflow
    except ImportError:
        pass # Handle later if needed or just let it fail if used
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.stop()

st.set_page_config(layout="wide", page_title="Dataset Tools WebUI")

# --- Helper Functions ---
async def run_upscale_task(image_path, comfy_url, model_name, scale_by):
    workflow_path = "放大工作流.json"
    if not os.path.exists(workflow_path):
        return None, f"找不到工作流文件: {workflow_path}"
    
    # 使用绝对路径以防ComfyUI库找不到
    workflow_path = os.path.abspath(workflow_path)
    output_dir = os.path.abspath("outputs/temp")
    os.makedirs(output_dir, exist_ok=True)

    try:
        async with ComfyUIClient(comfy_url) as client:
            upload_info = await client.upload_file(image_path)
            server_filename = upload_info['name']
            
            workflow = ComfyWorkflow(workflow_path)
            # 根据 JSON ID 替换
            workflow.add_replacement("5", "image", server_filename)
            workflow.add_replacement("1", "model_name", model_name)
            workflow.add_replacement("3", "scale_by", scale_by)
            
            # 指定输出节点
            workflow.add_output_node("4")
            
            print("提交工作流...")
            results = await client.execute_workflow(workflow, output_dir)
            
            if "4" in results and "DEFAULT_DOWNLOAD" in results["4"]:
                files = results["4"]["DEFAULT_DOWNLOAD"]
                if isinstance(files, list) and files:
                    return files[0], None
                elif isinstance(files, str):
                    return files, None
            
            return None, "工作流执行完成但未找到输出文件"
            
    except Exception as e:
        return None, str(e)

def replace_image_file(original_path, new_path):
    try:
        orig_dir = os.path.dirname(original_path)
        orig_name = os.path.splitext(os.path.basename(original_path))[0]
        new_ext = os.path.splitext(new_path)[1]
        
        target_path = os.path.join(orig_dir, orig_name + new_ext)
        
        # 如果目标路径与原路径不同（例如扩展名变了），先删除原文件
        if os.path.normpath(original_path) != os.path.normpath(target_path):
            if os.path.exists(original_path):
                os.remove(original_path)
            
        # 移动新文件到目标位置
        if os.path.exists(target_path):
            os.remove(target_path) # 确保覆盖
            
        shutil.move(new_path, target_path)
        return target_path, None
    except Exception as e:
        return None, str(e)

@st.dialog("全屏预览", width="large")
def open_zoom_modal(image_path):
    # 强制修改 Dialog 宽度为 95% 视窗宽度
    st.markdown("""
        <style>
            div[data-testid="stDialog"] div[role="dialog"] {
                width: 95vw !important;
                max-width: 95vw !important;
            }
        </style>
    """, unsafe_allow_html=True)
    st_zoomable_image(image_path, height=1000)

# --- Custom CSS ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .stTextArea textarea {
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("数据集工具箱")
page = st.sidebar.radio("选择功能", [
    "Gallery Editor (图库编辑)",
    "LoRA Downloader (素材下载)",
    "Add Prefix (添加标签前缀)",
    "Check Matches (检查匹配)",
    "Delete Useless TXT (清理TXT)",
    "Drop Tag (删减标签)",
    "Fill Transparent (填充背景)",
    "Merge Folders (合并文件夹)",
    "Hash Deduplication (哈希去重)",
    "SauceNAO (搜图)",
    "WIP: Tagger (自动打标)"
])

# --- Pages ---

def render_gallery_editor():
    st.header("🖼️ 图库预览与编辑")
    
    col_sel, col_info = st.columns([3, 1])
    with col_sel:
        target_dir = st_directory_selector(st.empty(), key="gallery_dir", initial_path=".")
    
    if not os.path.exists(target_dir):
        st.warning("请选择有效的文件夹")
        return

    # 获取图片列表
    images = get_image_files(target_dir)
    if not images:
        st.info("当前文件夹没有图片。")
        return

    # 分页/选择状态
    if 'gallery_idx' not in st.session_state:
        st.session_state.gallery_idx = 0
    
    # 确保索引在范围内
    if st.session_state.gallery_idx >= len(images):
        st.session_state.gallery_idx = len(images) - 1
    if st.session_state.gallery_idx < 0:
        st.session_state.gallery_idx = 0

    current_image_path = images[st.session_state.gallery_idx]
    
    # 导航栏
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ 上一张"):
            st.session_state.gallery_idx = (st.session_state.gallery_idx - 1) % len(images)
            st.rerun()
    with c3:
        if st.button("下一张 ➡️"):
            st.session_state.gallery_idx = (st.session_state.gallery_idx + 1) % len(images)
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align: center'><b>{st.session_state.gallery_idx + 1} / {len(images)}</b> : {os.path.basename(current_image_path)}</div>", unsafe_allow_html=True)

    # 放大预览比对界面
    if 'upscale_preview' in st.session_state and st.session_state['upscale_preview']['orig'] == current_image_path:
        with st.container():
            st.info("🔍 放大结果比对确认")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.image(current_image_path, caption="原始图片", width='stretch')
                _, res_old = get_file_info(current_image_path)
                st.caption(f"原始分辨率: {res_old}")
            with p_col2:
                new_path = st.session_state['upscale_preview']['new']
                if os.path.exists(new_path):
                    st.image(new_path, caption="放大结果", width='stretch')
                    _, res_new = get_file_info(new_path)
                    st.caption(f"新分辨率: {res_new}")
                else:
                    st.error("预览文件已丢失")
                
            b1, b2 = st.columns(2)
            if b1.button("✅ 确认替换", type="primary", width='stretch'):
                 final, err = replace_image_file(current_image_path, st.session_state['upscale_preview']['new'])
                 if final:
                     st.success(f"已替换: {os.path.basename(final)}")
                     del st.session_state['upscale_preview']
                     time.sleep(0.5)
                     st.rerun()
                 else:
                     st.error(f"替换失败: {err}")
            
            if b2.button("❌ 放弃更改", width='stretch'):
                 del st.session_state['upscale_preview']
                 st.rerun()
            st.markdown("---")

    # 主视图
    view_col, edit_col = st.columns([1.5, 1])
    
    with view_col:
        try:
            # 获取图片信息
            size_str, resolution = get_file_info(current_image_path)
            
            # 顶部工具栏：信息 + 放大按钮
            col_info, col_zoom = st.columns([8, 1])
            with col_info:
                 st.info(f"📏 {resolution}  |  💾 {size_str}")
            with col_zoom:
                 if st.button("🔭", help="全屏放大模式 (支持滚轮缩放/拖拽)"):
                     open_zoom_modal(current_image_path)

            # 图片显示 (普通静态模式)
            # 使用 container_width 适应宽度
            st.image(current_image_path, width='stretch')
            
            # ComfyUI 放大工具栏
            with st.expander("🧩 ComfyUI 图片放大", expanded=False):
                c_url, c_model = st.columns(2)
                comfy_url = c_url.text_input("ComfyUI URL", "http://127.0.0.1:8188")
                model_name = c_model.text_input("Model Name", "RealESRGAN_x4plus_anime_6B.pth")
                
                c_scale, c_check = st.columns(2)
                scale_by = c_scale.number_input("Scale By", 0.1, 2.0, 0.25, 0.1, help="放大模型(通常4x)放大后再进行的缩放。0.5 = 最终2x")
                auto_replace = c_check.checkbox("自动覆盖 (无需确认)", value=False)
                
                if st.button("🚀 执行放大", width='stretch'):
                    with st.spinner("正在发送至 ComfyUI 处理..."):
                        new_path, err = asyncio.run(run_upscale_task(current_image_path, comfy_url, model_name, scale_by))
                        if new_path:
                            if auto_replace:
                                final_path, err_rep = replace_image_file(current_image_path, new_path)
                                if final_path:
                                    st.success(f"已替换为: {os.path.basename(final_path)}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"替换失败: {err_rep}")
                            else:
                                st.session_state['upscale_preview'] = {'orig': current_image_path, 'new': new_path}
                                st.rerun()
                        else:
                            st.error(f"处理失败: {err}")
            
        except Exception as e:
            st.error(f"无法加载图片: {e}")

    with edit_col:
        # TXT 编辑
        content, txt_path = get_txt_content(current_image_path)
        new_content = st.text_area("Tags / Caption", value=content, height=400, key=f"txt_{current_image_path}")
        
        c_save, c_del = st.columns(2)
        with c_save:
            if st.button("💾 保存 TXT"):
                if save_txt_content(txt_path, new_content):
                    st.success("已保存")
                else:
                    st.error("保存失败")
        
        with c_del:
            if st.button("🗑️ 删除 图片+TXT", type="primary"):
                try:
                    os.remove(current_image_path)
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                    st.success("已删除")
                    # 移到下一张
                    if st.session_state.gallery_idx >= len(images) - 1:
                        st.session_state.gallery_idx = max(0, len(images) - 2)
                    st.rerun()
                except Exception as e:
                    st.error(f"删除失败: {e}")

def render_downloader():
    st.header("⬇️ LoRA 训练素材下载器")
    
    col_settings, col_editor = st.columns([1, 1])

    with col_settings:
        st.subheader("设置")
        # 目录选择
        st.markdown("##### 保存目录")
        save_dir = st_directory_selector(st.empty(), key="dl_save_dir", initial_path="downloaded_images")
        
        c1, c2 = st.columns(2)
        with c1:
            max_images = st.number_input("每个标签最大下载数", value=50)
            timeout = st.number_input("超时 (ms)", value=5000)
        with c2:
            max_batch = st.number_input("每批处理行数", value=5)
            start_line = st.number_input("起始行号", value=1)
            
        use_proxy = st.checkbox("使用代理", value=True)
        proxy_url = st.text_input("代理地址", "http://127.0.0.1:7890")
        
        proxies = {"http://": proxy_url, "https://": proxy_url} if use_proxy else None
        
        # 选择 Tags 文件
        st.markdown("##### 标签列表文件")
        # 列出当前目录下的 txt 文件
        try:
            txt_files = [f for f in os.listdir(".") if f.lower().endswith(".txt")]
        except:
            txt_files = []
        
        if not txt_files:
            txt_files = ["新建文件..."]
        else:
            txt_files = ["新建文件..."] + txt_files
            
        selected_txt = st.selectbox("选择或新建", txt_files, index=1 if len(txt_files)>1 else 0)
        
        if selected_txt == "新建文件...":
            txt_path = st.text_input("新文件名 (例如 tags.txt)")
        else:
            txt_path = selected_txt

    with col_editor:
        st.subheader("编辑标签列表")
        file_content = ""
        if txt_path and os.path.exists(txt_path) and os.path.isfile(txt_path):
             try:
                 with open(txt_path, 'r', encoding='utf-8') as f:
                     file_content = f.read()
             except:
                 st.warning("无法读取文件内容")
        
        new_content = st.text_area("内容 (每行一个配置)", value=file_content, height=400, placeholder="例如: 1girl solo")
        
        if st.button("💾 保存标签文件"):
            if txt_path:
                try:
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    st.success(f"已保存到 {txt_path}")
                    # st.rerun() 
                except Exception as e:
                    st.error(f"保存失败: {e}")
            else:
                st.error("请输入文件名")

    st.markdown("---")
    if st.button("开始下载", type="primary"):
        if not txt_path or not os.path.exists(txt_path):
            st.error("请选择或创建一个有效的 TXT 文件")
            return
            
        status = st.empty()
        status.info("正在初始化下载任务...")
        
        async def run_task():
            await downloader.run_downloader(
                txt_path=txt_path,
                save_dir=save_dir,
                timeout=timeout,
                proxies=proxies,
                max_lines_per_batch=max_batch,
                max_images=max_images,
                start_line=start_line
            )
            
        asyncio.run(run_task())
        status.success("任务完成！")

def render_add_prefix():
    st.header("🏷️ 批量添加前缀")
    st.info("给文件夹内所有 TXT 文件的开头添加指定 Tag")
    
    target_dir = st_directory_selector(st.empty(), key="prefix_dir", initial_path=".")
    prefix = st.text_input("要添加的前缀 (例如: <style>bacg</style>)")
    
    if st.button("执行添加"):
        if not prefix:
            st.error("前缀不能为空")
        with st.status("正在处理...", expanded=True) as status:
            st.write("正在扫描并修改文件...")
            f = io.StringIO()
            try:
                with contextlib.redirect_stdout(f):
                    add_prefix.batch_add_prefix_to_txt(target_dir, prefix)
                
                output = f.getvalue()
                status.update(label="✅ 处理完成", state="complete", expanded=True)
                
                # 显示日志
                if output:
                    st.text_area("执行日志", value=output, height=300)
                else:
                    st.success("操作完成 (无输出日志)")
                    
            except Exception as e:
                status.update(label="❌ 发生错误", state="error")
                st.error(f"出错: {e}")
                st.text_area("错误日志", value=f.getvalue(), height=300)

def render_check_matches():
    st.header("🔍 检查文件匹配")
    target_dir = st_directory_selector(st.empty(), key="match_dir", initial_path=".")
    
    if st.button("检查", type="primary"):
        with st.spinner("正在扫描目录..."):
            img_no_txt, txt_no_img = check_matches.check_matching_files(target_dir)
        
        if not img_no_txt and not txt_no_img:
            st.canvas = st.balloons()
            st.success("✨ 完美！所有图片都有对应的 TXT，且所有 TXT 都有对应的图片。")
            return

        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"图片无TXT ({len(img_no_txt)})")
            if img_no_txt:
                st.error("以下图片缺少 TXT 文件:")
                st.write(list(img_no_txt))
            else:
                st.success("✔ 没有缺失 TXT 的图片")
                
        with c2:
            st.subheader(f"TXT无图片 ({len(txt_no_img)})")
            if txt_no_img:
                st.error("以下 TXT 文件缺少对应图片:")
                st.write(list(txt_no_img))
            else:
                st.success("✔ 没有孤立的 TXT 文件")
            st.subheader(f"TXT无图片 ({len(txt_no_img)})")
            st.write(txt_no_img)

def render_delete_useless():
    st.header("🧹 删除无对应图片的 TXT")
    target_dir = st_directory_selector(st.empty(), key="del_useless_dir", initial_path=".")
    
    if st.button("扫描并删除"):
        count, logs = delete_unmatched_txt_files_func(target_dir)
        st.success(f"已删除 {count} 个文件")
        with st.expander("删除详情"):
            for log in logs:
                st.text(log)

def render_drop_tag():
    st.header("🎲 随机删除 Tag")
    st.info("根据概率随机删除 TXT 中的 tags (格式: tag1, tag2 || tag3, ...)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 输入文件夹")
        in_dir = st_directory_selector(st.empty(), key="drop_in", initial_path=".")
    with col2:
        st.markdown("##### 输出文件夹")
        out_dir = st_directory_selector(st.empty(), key="drop_out", initial_path="./output_dropped")
    
    rates_str = st.text_input("保留率列表 (逗号分隔，例如: 0.3, 0.5)", "0.3, 0.5")
    
    if st.button("执行处理"):
        with st.status("处理中...", expanded=True) as status:
            f = io.StringIO()
            try:
                rates = [float(x.strip()) for x in rates_str.split(',')]
                with contextlib.redirect_stdout(f):
                    drop_tag.process_all_files(in_dir, out_dir, rates)
                
                output = f.getvalue()
                status.update(label="✅ 处理完成", state="complete", expanded=True)
                st.text_area("执行日志", value=output, height=300)
                
            except Exception as e:
                status.update(label="❌ 发生错误", state="error")
                st.error(f"出错: {e}")
                st.text_area("错误日志", value=f.getvalue(), height=300)

def render_fill_img():
    st.header("⬜ 填充透明背景为白色")
    
    st.markdown("##### 输入文件夹")
    in_dir = st_directory_selector(st.empty(), key="fill_in", initial_path=".")
    
    if st.button("执行"):
        with st.status("处理中...", expanded=True) as status:
            f = io.StringIO()
            try:
                with contextlib.redirect_stdout(f):
                    fill_img.process_folder(in_dir)
                
                output = f.getvalue()
                status.update(label="✅ 完成", state="complete", expanded=True)
                if output:
                    st.text_area("详细日志", output, height=300)
                else:
                    st.info("没有产生输出日志 (可能没有需要处理的文件)")
                    
            except Exception as e:
                status.update(label="❌ 错误", state="error")
                st.error(f"出错: {e}")

def render_merge_folders():
    st.header("📂 归并子文件夹文件")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 源文件夹 (包含子目录)")
        src = st_directory_selector(st.empty(), key="merge_src", initial_path=".")
    with col2:
        st.markdown("##### 目标文件夹")
        dst = st_directory_selector(st.empty(), key="merge_dst", initial_path="./merged_output")
    
    if st.button("开始移动"):
        with st.status("正在移动文件...", expanded=True) as status:
            f = io.StringIO()
            try:
                with contextlib.redirect_stdout(f):
                    merge_folders.move_files_from_subfolders(src, dst)
                
                output = f.getvalue()
                status.update(label="✅ 移动完成", state="complete", expanded=True)
                st.text_area("移动日志", output, height=300)
                
            except Exception as e:
                status.update(label="❌ 错误", state="error")
                st.error(f"出错: {e}")

def render_hash_dedup():
    st.header("🧩 哈希去重")
    target_dir = st_directory_selector(st.empty(), key="hash_dir", initial_path=".")
    threshold = st.slider("相似度阈值 (越小越相似)", 0, 20, 5)
    
    if 'hash_groups' not in st.session_state:
        st.session_state.hash_groups = None

    if st.button("扫描重复图片"):
        with st.spinner("正在计算哈希..."):
            st.session_state.hash_groups = find_duplicate_images(target_dir, threshold)
        
    if st.session_state.hash_groups:
        st.write(f"发现 {len(st.session_state.hash_groups)} 组重复图片")
        
        mode = st.radio("处理模式", ["仅查看", "自动删除无TXT的副本", "自动删除副本(保留最高分辨率)"])
        
        if st.button("执行处理/显示详情"):
            method = 'manual'
            delete_txt = False
            
            if mode == "自动删除无TXT的副本":
                method = 'auto_no_txt'
            elif mode == "自动删除副本(保留最高分辨率)":
                method = 'auto_all'
                delete_txt = st.checkbox("同时删除对应的TXT", value=True)
            
            results = process_duplicate_groups(st.session_state.hash_groups, method, delete_txt)
            
            if method == 'manual':
                for item in results:
                    st.markdown("---")
                    for img in item['group']:
                        st.write(f"{'✅' if img['has_txt'] else '❌'} {img['path']} ({img['resolution']}px)")
                        st.image(img['path'], width=200)
            else:
                st.write(results)
                st.session_state.hash_groups = None # 清除状态

def render_saucenao():
    st.header("🔎 SauceNAO 搜图")
    # 简化的界面，直接调用 API
    api_key = st.text_input("SauceNAO API Key", type="password")
    if not api_key:
        st.warning("需要 API Key")
        return
        
    target_path = st_directory_selector(st.empty(), key="sauce_dir", initial_path=".")
    
    if st.button("开始搜图"):
        st.info("Check console for progress...")
        # 为了简单，直接调用 main，需自行调整 sauce_api_key_list
        # 由于原脚本结构较紧耦合，这里建议用户直接后台跑，或稍后重构。
        # 尝试直接调用 (需要注意 API Key 传递)
        async def run_sauce():
            await saucenao.main(
                target_path, "json", True, None, 
                sauce_api_key_list=[api_key],
                danbooru_api_key_list=[]
            )
        asyncio.run(run_sauce())
        st.success("完成")

import tagger_api

def render_tagger():
    st.header("🏷️ 批量自动打标 (Tagger)")
    
    # 1. API 配置
    st.markdown("### 1. API 连接")
    base_url = st.text_input("API URL", "http://127.0.0.1:5000/tagger/v1", help="Tagger 后端服务的完整地址，例如 http://127.0.0.1:5000/tagger/v1")
    
    client = None
    available_models = []
    
    # 获取模型列表
    if 'tagger_models' not in st.session_state:
        st.session_state.tagger_models = None
        
    col_connect, col_status = st.columns([1, 4])
    with col_connect:
        if st.button("🔌 连接/刷新"):
            client = TaggerAPIClient(base_url)
            try:
                with st.spinner("正在连接 API..."):
                    resp = client.get_available_models()
                if resp and 'models' in resp:
                    st.session_state.tagger_models = resp['models']
                    st.success("连接成功")
                else:
                    st.error("连接失败或无法获取模型列表")
                    st.session_state.tagger_models = None
            except Exception as e:
                st.error(f"错误: {e}")
                st.session_state.tagger_models = None

    if st.session_state.tagger_models:
        st.success(f"已连接，发现 {len(st.session_state.tagger_models)} 个模型")
    else:
        st.warning("⚠️ 请先连接 Tagger API 服务")
        return

    st.markdown("---")

    # 2. 文件夹和参数
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 2. 输入设置")
        image_dir = st_directory_selector(st.empty(), key="tagger_img_dir", initial_path=".")
        
        # 模型选择
        model_name = st.selectbox("选择模型", st.session_state.tagger_models, index=0)
        
        fixed_prefix = st.text_input("固定前缀 Tags (可选)", placeholder="例如: <style>art</style>")

    with c2:
        st.markdown("### 3. 参数微调")
        threshold = st.slider("常规 Tag 阈值", 0.0, 1.0, 0.35, 0.01)
        char_threshold = st.slider("角色 Tag 阈值", 0.0, 1.0, 0.85, 0.01)
        
        general_mcut = st.checkbox("启用 General MCUT")
        char_mcut = st.checkbox("启用 Character MCUT")
        
        overwrite = st.checkbox("覆盖已存在的 TXT", value=False, help="如果不勾选，新 Tags 将会被追加到现有文件末尾")

    st.markdown("---")

    # 3. 执行
    if st.button("🚀 开始批量打标", type="primary"):
        if not os.path.isdir(image_dir):
            st.error("请输入有效的图片文件夹路径")
            return
            
        client = TaggerAPIClient(base_url)
        
        # 收集图片
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        target_files = [
            os.path.join(image_dir, f) 
            for f in os.listdir(image_dir) 
            if os.path.splitext(f)[1].lower() in image_exts
        ]
        
        if not target_files:
            st.warning("目录中没有找到图片文件")
            return

        progress_text = st.empty()
        progress_bar = st.progress(0)
        log_area = st.empty()
        logs = []
        
        failed_count = 0
        success_count = 0
        
        # 预定义排除列表
        EXCLUDE_SYMBOLS = tagger_api.main.__code__.co_consts[10] if hasattr(tagger_api.main, '__code__') else {"0_0", "o_o"} # fallback
        EXCLUDE_WORDS = {"general", "sensitive", "questionable", "explicit"}
        try:
             # 尝试从 tagger_api 中提取常量，或者直接硬编码一份，为了稳健这里直接硬编码一份常用的
             EXCLUDE_SYMBOLS = {"0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", "<|>_<|>", "=_=", ">_<", "3_3", "6_9", ">_o", "@_@", "^_^", "o_o", "u_u", "x_x", "|_|", "||_||"}
        except:
             pass

        stop_button = st.button("停止任务")

        for i, img_path in enumerate(target_files):
            if stop_button:
                break
                
            fname = os.path.basename(img_path)
            progress_text.text(f"正在处理 ({i+1}/{len(target_files)}): {fname}")
            
            try:
                # 调用 API
                result = client.interrogate_image(
                    image_path=img_path,
                    model=model_name,
                    threshold=threshold,
                    character_threshold=char_threshold,
                    general_mcut_enabled=general_mcut,
                    character_mcut_enabled=char_mcut
                )
                
                if result and 'caption' in result:
                    raw_tags = list(result['caption'].keys())
                    # 处理 Tags
                    processed = []
                    for t in raw_tags:
                        if t not in EXCLUDE_WORDS:
                             processed.append(t.replace('_', ' ') if t not in EXCLUDE_SYMBOLS else t)
                    
                    # 保存
                    txt_path = os.path.splitext(img_path)[0] + ".txt"
                    
                    final_tags = processed
                    
                    # 如果不是覆盖模式，且文件存在
                    if not overwrite and os.path.exists(txt_path):
                        try:
                            with open(txt_path, 'r', encoding='utf-8') as f:
                                old_content = f.read().strip()
                            # 简单的去重追加逻辑
                            old_tags = [t.strip() for t in old_content.split(',') if t.strip()]
                            new_unique = [t for t in processed if t not in old_tags]
                            final_tags = old_tags + new_unique
                        except:
                            pass # 读取失败就直接覆盖吧
                    
                    # 添加前缀
                    content_str = ", ".join(final_tags)
                    if fixed_prefix and not content_str.startswith(fixed_prefix):
                         content_str = f"{fixed_prefix}, {content_str}"
                         
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(content_str)
                        
                    logs.append(f"✅ {fname}: {len(processed)} tags")
                    success_count += 1
                else:
                    logs.append(f"❌ {fname}: API返回空或失败")
                    failed_count += 1
                    
            except Exception as e:
                logs.append(f"❌ {fname}: {str(e)}")
                failed_count += 1

            # 更新进度
            progress_bar.progress((i + 1) / len(target_files))
            # 实时显示最近几条日志
            log_area.text_area("执行日志", "\n".join(logs[-10:]), height=200)

        st.success(f"任务结束！成功: {success_count}, 失败: {failed_count}")

# --- Router ---
if page == "Gallery Editor (图库编辑)":
    render_gallery_editor()
elif page == "LoRA Downloader (素材下载)":
    render_downloader()
elif page == "Add Prefix (添加标签前缀)":
    render_add_prefix()
elif page == "Check Matches (检查匹配)":
    render_check_matches()
elif page == "Delete Useless TXT (清理TXT)":
    render_delete_useless()
elif page == "Drop Tag (删减标签)":
    render_drop_tag()
elif page == "Fill Transparent (填充背景)":
    render_fill_img()
elif page == "Merge Folders (合并文件夹)":
    render_merge_folders()
elif page == "Hash Deduplication (哈希去重)":
    render_hash_dedup()
elif page == "SauceNAO (搜图)":
    render_saucenao()
elif page == "WIP: Tagger (自动打标)":
    render_tagger()

