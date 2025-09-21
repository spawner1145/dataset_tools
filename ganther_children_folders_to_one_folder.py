import os
import shutil
from pathlib import Path

def move_files_from_subfolders(source_dir, target_dir):
    # 确保目标文件夹存在，如果不存在则创建
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isdir(item_path):
            if item_path == target_dir:
                continue
            move_files_from_subfolders(item_path, target_dir)
        elif os.path.isfile(item_path):
            target_file_path = os.path.join(target_dir, item)
            counter = 1
            while os.path.exists(target_file_path):
                file_name, file_ext = os.path.splitext(item)
                target_file_path = os.path.join(target_dir, f"{file_name}({counter}){file_ext}")
                counter += 1
            try:
                shutil.move(item_path, target_file_path)
                print(f"已移动: {item_path} -> {target_file_path}")
            except Exception as e:
                print(f"移动文件时出错 {item_path}: {str(e)}")

if __name__ == "__main__":
    # 修改为你的源文件夹路径
    source_directory = "emilia"
    # 修改为你的目标文件夹路径
    target_directory = "emilia/12_emilia"
    
    if not os.path.exists(source_directory):
        print(f"错误: 源文件夹 '{source_directory}' 不存在")
    else:
        print(f"开始移动文件，从 '{source_directory}' 到 '{target_directory}'")
        move_files_from_subfolders(source_directory, target_directory)
        print("文件移动完成")
    