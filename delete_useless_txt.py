import os

def delete_unmatched_txt_files():
    # 硬编码要处理的文件夹路径
    folder_path = "emilia"  # 替换为你的文件夹路径
    
    # 硬编码支持的图片扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    if not os.path.exists(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return
    if not os.path.isdir(folder_path):
        print(f"错误: '{folder_path}' 不是一个文件夹")
        return
    
    deleted_count = 0

    for filename in os.listdir(folder_path):
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
                    print(f"已删除: {txt_file_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"删除失败 {txt_file_path}: {str(e)}")
    
    print(f"\n处理完成。共{deleted_count}个TXT文件被删除。")

if __name__ == "__main__":
    delete_unmatched_txt_files()
