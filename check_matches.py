import os

# 将此处修改为你的目标文件夹路径
TARGET_FOLDER = "emilia"  # 例如: "C:/images" 或 "/home/user/pictures"

def get_files_by_extension(folder_path, extensions):
    """获取文件夹中指定扩展名的所有文件（不含扩展名的文件名）"""
    files = set()
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            name, ext = os.path.splitext(filename)
            if ext.lower() in extensions:
                files.add(name)
    return files

def check_matching_files(folder_path):
    """检查图片文件和txt文件的匹配情况"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    txt_extensions = {'.txt'}

    image_files = get_files_by_extension(folder_path, image_extensions)
    txt_files = get_files_by_extension(folder_path, txt_extensions)
    images_without_txt = image_files - txt_files
    txt_without_images = txt_files - image_files

    return images_without_txt, txt_without_images

def main():
    if not os.path.isdir(TARGET_FOLDER):
        print(f"错误：文件夹 '{TARGET_FOLDER}' 不存在")
        return
    images_without_txt, txt_without_images = check_matching_files(TARGET_FOLDER)
    print(f"正在检查的文件夹: {os.path.abspath(TARGET_FOLDER)}")

    if images_without_txt:
        print(f"发现 {len(images_without_txt)} 个没有对应TXT文件的图片:")
        for name in sorted(images_without_txt):
            print(f"  - {name} (图片文件存在，但无同名TXT)")
    else:
        print("所有图片都有对应的TXT文件")


    if txt_without_images:
        print(f"发现 {len(txt_without_images)} 个没有对应图片的TXT文件:")
        for name in sorted(txt_without_images):
            print(f"  - {name}.txt (TXT文件存在，但无同名图片)")
    else:
        print("所有TXT文件都有对应的图片")

if __name__ == "__main__":
    main()
    