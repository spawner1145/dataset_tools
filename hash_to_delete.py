import os
import imagehash
from PIL import Image
from collections import defaultdict

def get_image_phash(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except Exception as e:
        print(f"无法处理图片 {image_path}: {e}")
        return None

def get_image_resolution(image_path):
    try:
        with Image.open(image_path) as img:
            return img.width * img.height
    except Exception as e:
        print(f"无法获取图片分辨率 {image_path}: {e}")
        return 0

def hamming_distance(hash1, hash2):
    return hash1 - hash2

def group_similar_images(directory, threshold=5):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    image_hashes = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in image_extensions and os.path.isfile(file_path):
            phash = get_image_phash(file_path)
            if phash:
                image_hashes[file_path] = phash
    
    groups = []
    processed = set()
    
    for path1, hash1 in image_hashes.items():
        if path1 in processed:
            continue
            
        group = [path1]
        processed.add(path1)
        
        for path2, hash2 in image_hashes.items():
            if path2 not in processed and hamming_distance(hash1, hash2) <= threshold:
                group.append(path2)
                processed.add(path2)
        
        if len(group) > 1:
            groups.append(group)
    
    return groups

def process_similar_groups(groups, delete_files=False, delete_txt_files=False):
    if not groups:
        print("未发现相似图片组")
        return
    
    deleted_image_count = 0
    deleted_txt_count = 0
    
    for i, group in enumerate(groups, 1):
        print(f"\n相似图片组 #{i} ({len(group)} 张图片):")
        
        has_txt = []
        no_txt = []
        
        for file_path in group:
            txt_path = os.path.splitext(file_path)[0] + '.txt'
            if os.path.exists(txt_path):
                has_txt.append({
                    'image_path': file_path,
                    'txt_path': txt_path,
                    'resolution': get_image_resolution(file_path)
                })
                print(f"[有TXT] {os.path.basename(file_path)} - 分辨率: {has_txt[-1]['resolution']} 像素")
            else:
                no_txt.append(file_path)
                print(f"[无TXT] {os.path.basename(file_path)}")
        
        if delete_files:
            if has_txt:
                if no_txt:
                    print(f"该组包含带TXT的图片，将删除所有无TXT的相似图片")
                    
                    for file_path in no_txt:
                        try:
                            os.remove(file_path)
                            deleted_image_count += 1
                            print(f"已删除图片: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"删除 {os.path.basename(file_path)} 失败: {e}")
            else:
                if no_txt and len(no_txt) > 1:
                    no_txt_sorted = sorted(no_txt, key=lambda x: get_image_resolution(x), reverse=True)
                    to_keep = no_txt_sorted[0]
                    to_delete = no_txt_sorted[1:]
                    
                    print(f"将保留无TXT图片（最高分辨率）: {os.path.basename(to_keep)}")
                    
                    for file_path in to_delete:
                        try:
                            os.remove(file_path)
                            deleted_image_count += 1
                            print(f"已删除图片: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"删除 {os.path.basename(file_path)} 失败: {e}")
        
        if delete_txt_files and has_txt and len(has_txt) > 1:
            has_txt_sorted = sorted(has_txt, key=lambda x: x['resolution'], reverse=True)
            to_keep = has_txt_sorted[0]
            to_delete = has_txt_sorted[1:]
            
            print(f"将保留带TXT图片（最高分辨率）: {os.path.basename(to_keep['image_path'])}")
            
            for item in to_delete:
                try:
                    os.remove(item['image_path'])
                    deleted_image_count += 1
                    print(f"已删除图片: {os.path.basename(item['image_path'])}")
                    
                    if os.path.exists(item['txt_path']):
                        os.remove(item['txt_path'])
                        deleted_txt_count += 1
                        print(f"已删除对应TXT: {os.path.basename(item['txt_path'])}")
                except Exception as e:
                    print(f"删除 {os.path.basename(item['image_path'])} 失败: {e}")
    
    if delete_files or delete_txt_files:
        print(f"\n处理完成，共删除 {deleted_image_count} 个重复图片和 {deleted_txt_count} 个对应的TXT文件")

if __name__ == "__main__":
    target_directory = "emilia"  # 替换为实际目录
    
    if not os.path.isdir(target_directory):
        print(f"错误: 目录 '{target_directory}' 不存在")
    else:
        try:
            # 获取用户输入的阈值
            threshold_input = input("输入相似度阈值（建议3-10，值越小越相似）: ")
            threshold = int(threshold_input)
            
            print(f"正在分析目录: {target_directory}，请稍候...")
            similar_groups = group_similar_images(target_directory, threshold)
            process_similar_groups(similar_groups, delete_files=False, delete_txt_files=False)

            delete_choice = input("\n是否删除无TXT的重复文件？(y/n): ").strip().lower()
            delete_files = (delete_choice == 'y')

            delete_txt_files = False
            if delete_files:
                txt_choice = input("是否同时处理带TXT的重复文件？(会保留分辨率最高的，删除其他及对应TXT)(y/n): ").strip().lower()
                delete_txt_files = (txt_choice == 'y')
            
            if delete_files or delete_txt_files:
                confirm = input("确定要执行删除操作吗？这将永久删除文件！(y/n): ").strip().lower()
                if confirm == 'y':
                    process_similar_groups(similar_groups, delete_files, delete_txt_files)
                else:
                    print("已取消删除操作")
            else:
                print("已取消删除操作")
                
        except ValueError:
            print("错误: 请输入有效的数字作为阈值")
        except Exception as e:
            print(f"发生错误: {e}")
    