import httpx
import asyncio
import aiofiles
import os
import re
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import json
from urllib.parse import quote

# 需要保留下划线的特殊符号集合
EXCLUDE_SYMBOLS = {"0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", 
                   "<|>_<|>", "=_=", ">_<", "3_3", "6_9", ">_o", "@_@", 
                   "^_^", "o_o", "u_u", "x_x", "|_|", "||_||"}

async def download_image(session, item, filename, save_dir, error_flag, line_number):
    max_retries = 10
    retries = 0
    
    media_asset = item.get('media_asset', {})
    variants = media_asset.get('variants', [])
    original_variant = next((v for v in variants if v['type'] == 'original'), None)
    url = original_variant['url'] if original_variant else item.get('file_url')
    
    if not url:
        print(f"未找到原始图片URL: {item.get('id', '未知ID')}")
        return False

    while retries < max_retries:
        try:
            response = await session.get(url)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'video' in content_type:
                    print(f"跳过视频文件: {url}")
                    return False
                
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(response.content)
                
                if filename.suffix.lower() == '.webp':
                    new_filename = filename.with_suffix('.jpg')
                    try:
                        with Image.open(filename) as img:
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')
                            img.save(new_filename, 'JPEG', quality=95)
                        os.remove(filename)
                        filename = new_filename
                        print(f"转换完成: {filename}")
                    except UnidentifiedImageError:
                        print(f"WebP文件损坏，无法转换: {filename}")
                        os.remove(filename)
                        return False
                    except Exception as e:
                        print(f"WebP转换异常: {e} - {filename}")
                        os.remove(filename)
                        return False
                
                print(f"下载完成: {filename}")
                
                tag_string = item.get('tag_string', '')
                processed_tags = tag_string.replace(' ', ',').replace('_', ' ')
                txt_filename = filename.with_suffix('.txt')
                async with aiofiles.open(txt_filename, 'w', encoding='utf-8') as txt_file:
                    await txt_file.write(processed_tags)
                print(f"写入TXT: {txt_filename}")
                
                return True
            else:
                print(f"下载失败 (状态码 {response.status_code}): {url}")
                break
        except Exception as e:
            print(f"下载异常 (尝试 {retries + 1}/{max_retries}): {e} - {url}")
            retries += 1
    
    print(f"放弃下载: {url}")
    error_flag['value'] = True
    error_flag['lines'].append(line_number)
    return False

async def process_line(session, line, line_number, base_save_dir, max_images=5, existing_filenames=None, error_flag=None):
    stripped_line = line.strip()
    keywords = [kw for kw in stripped_line.split(' ') if kw]
    processed_keywords_for_folder = []
    for kw in keywords:
        if kw in EXCLUDE_SYMBOLS:
            processed_keywords_for_folder.append(kw)
        else:
            processed_keywords_for_folder.append(kw.replace('_', ' '))
    folder_name_raw = ' '.join(processed_keywords_for_folder)
    invalid_chars = r'[\\/:*?"<>|]'
    folder_name = re.sub(invalid_chars, '_', folder_name_raw).replace(' ', '_')
    save_dir = base_save_dir / folder_name
    
    try:
        save_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"创建文件夹失败: {e} - {save_dir}")
        error_flag['value'] = True
        error_flag['lines'].append(line_number)
        return
    processed_keywords_for_search = []
    for kw in keywords:
        if kw in EXCLUDE_SYMBOLS:
            encoded_kw = quote(kw)
        else:
            encoded_kw = quote(kw)
        processed_keywords_for_search.append(encoded_kw)
    
    search_tag = '++'.join(processed_keywords_for_search)
    print(f"构造搜索标签: {search_tag}")
    
    page = 1
    processed_count = 0
    
    while processed_count < max_images:
        url = f"https://kagamihara.donmai.us/posts.json?page={page}&tags={search_tag}"
        try:
            response = await session.get(url)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    print(f"无更多图片可下载: {search_tag} (第{page}页)")
                    break
                for item in data:
                    image_name = os.path.basename(item.get('file_url', ''))
                    if not image_name:
                        print(f"跳过无文件名的项目: {item.get('id', '未知ID')}")
                        continue
                    
                    comparison_filename = image_name
                    if comparison_filename.lower().endswith('.webp'):
                        comparison_filename = comparison_filename[:-5] + '.jpg'
                    
                    unique_filename = save_dir / comparison_filename
                    
                    if comparison_filename in existing_filenames:
                        print(f"文件已存在: {comparison_filename}, 跳过下载")
                        processed_count += 1
                        if processed_count >= max_images:
                            return
                    else:
                        success = await download_image(session, item, unique_filename, save_dir, error_flag, line_number)
                        if success:
                            processed_count += 1
                            existing_filenames.add(comparison_filename)
                            if processed_count >= max_images:
                                return
                        elif error_flag['value']:
                            return
            else:
                print(f"请求失败 (状态码 {response.status_code}): {url}")
                error_flag['value'] = True
                error_flag['lines'].append(line_number)
                return
        except Exception as e:
            print(f"请求异常: {e} - {url}")
            error_flag['value'] = True
            error_flag['lines'].append(line_number)
            return
        page += 1

async def read_existing_filenames(base_save_dir):
    existing_filenames = set()
    if not base_save_dir.exists():
        return existing_filenames
    for sub_dir in base_save_dir.glob('*'):
        if sub_dir.is_dir():
            for file in sub_dir.glob('*.jpg'):
                existing_filenames.add(file.name)
    return existing_filenames

async def main(txt_path, save_dir="downloaded_images", timeout=1000, proxies=None, start_line=1, max_lines_per_batch=5, max_images=5):
    print("开始执行脚本...")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"尝试打开文件: {txt_path}")

    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        proxies=proxies,
        limits=limits,
        follow_redirects=True
    ) as session:
        lines = []
        try:
            async with aiofiles.open(txt_path, mode='r', encoding='utf-8') as file:
                line_number = 0
                while True:
                    line = await file.readline()
                    if not line:
                        break
                    line_number += 1
                    stripped_line = line.strip()
                    if line_number >= start_line and stripped_line:
                        lines.append(stripped_line)
            print(f"成功读取文件: {txt_path}, 有效行数: {len(lines)} (从第{start_line}行开始)")
        except FileNotFoundError:
            print(f"错误: 文件 {txt_path} 不存在.")
            return None
        except UnicodeDecodeError:
            print(f"错误: 文件 {txt_path} 编码不是UTF-8，请转换为UTF-8后重试.")
            return None
        
        base_save_dir = Path(save_dir)
        base_save_dir.mkdir(parents=True, exist_ok=True)
        print(f"创建/检查基础保存目录: {base_save_dir}")

        existing_filenames = await read_existing_filenames(base_save_dir)
        print(f"已存在的图片文件数: {len(existing_filenames)}")
        
        error_flag = {'value': False, 'lines': []}
        batch_start_line = start_line
        while lines:
            batch_lines = lines[:max_lines_per_batch]
            lines = lines[max_lines_per_batch:]
            
            for i, line in enumerate(batch_lines, start=1):
                current_line_number = batch_start_line + i - 1
                print(f"\n处理第 {current_line_number} 行: {line}")
                await process_line(
                    session, line, current_line_number, base_save_dir,
                    max_images=max_images, existing_filenames=existing_filenames, error_flag=error_flag
                )
                if error_flag['value']:
                    error_lines = sorted(set(error_flag['lines']))
                    print(f"\n检测到下载异常，停止脚本。出错的行号: {', '.join(map(str, error_lines))}")
                    return min(error_lines)
        
            batch_start_line += max_lines_per_batch
    print("\n所有标签处理完成！")
    return None

if __name__ == "__main__":
    txt_path = "cailin.txt" # 所有你需要爬的标签txt，每行一个tag，不同tag会保存到不同的文件夹里，同一行可用空格分割代表必须有多个标签
    save_dir = "downloaded_images1"
    timeout = 5000
    proxies = {"http://": 'http://127.0.0.1:7890', "https://": 'http://127.0.0.1:7890'}
    max_lines_per_batch = 5
    max_images = 50 # 一个tag最多爬的图片数
    start_line = 1

    while True:
        result = asyncio.run(main(
            txt_path=txt_path,
            save_dir=save_dir,
            timeout=timeout,
            proxies=proxies,
            start_line=start_line,
            max_lines_per_batch=max_lines_per_batch,
            max_images=max_images
        ))
        if result is None:
            break
        else:
            start_line = result
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for line in f if line.strip())
        if start_line > total_lines:
            print(f"\n已处理完所有 {total_lines} 个有效标签，退出脚本。")
            break