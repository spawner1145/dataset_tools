import os
import glob

def batch_add_prefix_to_txt(folder_path, prefix):
    if not prefix:
        print("前缀为空，无需处理")
        return
        
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    
    if not txt_files:
        print(f"在文件夹 {folder_path} 中未找到任何txt文件")
        return
    
    print(f"找到 {len(txt_files)} 个txt文件，开始添加前缀...\n")
    
    for i, txt_path in enumerate(txt_files, 1):
        filename = os.path.basename(txt_path)
        print(f"处理文件 {i}/{len(txt_files)}: {filename}")
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content.startswith(prefix):
                print(f"  已包含前缀，跳过")
                continue
            
            if content:
                new_content = f"{prefix},{content}"
            else:
                new_content = prefix

            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  已添加前缀")
            
        except Exception as e:
            print(f"  处理失败: {str(e)}")
    
    print("\n批量处理完成")

if __name__ == "__main__":
    TXT_FOLDER = "blue_archive_game_cg"  # 包含txt文件的文件夹路径
    FIXED_PREFIX = "<style>bacg</style>"  # 要添加的前缀
    
    batch_add_prefix_to_txt(TXT_FOLDER, FIXED_PREFIX)
    