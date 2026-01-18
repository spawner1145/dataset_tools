import os
import random

def process_tag_file(input_path, output_path, drop_rates):
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parts = content.split("||")
        num_parts = len(parts)
        effective_rates = drop_rates[:num_parts]
        all_tags = []
        for i, part in enumerate(parts):
            raw_tags = part.split(',')
            cleaned_tags = [tag.strip() for tag in raw_tags if tag.strip()]
            if i < len(effective_rates):
                drop_rate = effective_rates[i]
                retained_tags = [tag for tag in cleaned_tags if random.random() <= drop_rate]
                all_tags.extend(retained_tags)
            else:
                all_tags.extend(cleaned_tags)
        processed_content = ",".join(all_tags)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
            
        print(f"已处理: {os.path.basename(input_path)}, 原始标签数: {len(all_tags)}, 分区数: {num_parts}")
        
    except Exception as e:
        print(f"处理文件 {os.path.basename(input_path)} 时出错: {str(e)}")

def process_all_files(input_dir, output_dir, drop_rates):
    os.makedirs(output_dir, exist_ok=True)
    
    # 保护列表
    PROTECTED_FILES = {'requirements.txt', 'cailin.txt', 'README.txt', 'LICENSE.txt', 'prompts.txt', 'config.txt'}

    for filename in os.listdir(input_dir):
        if filename in PROTECTED_FILES:
            continue

        if filename.endswith('.txt'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            if os.path.isfile(input_path):
                process_tag_file(input_path, output_path, drop_rates)
        elif os.path.isdir(os.path.join(input_dir, filename)):
            sub_input_dir = os.path.join(input_dir, filename)
            sub_output_dir = os.path.join(output_dir, filename)
            process_all_files(sub_input_dir, sub_output_dir, drop_rates)

if __name__ == "__main__":
    # 设置随机种子，确保结果可复现
    random.seed(42)
    input_directory = "/path/to/your/input/files"  # 输入文件夹路径
    output_directory = "/path/to/your/output/files"  # 输出文件夹路径
    
    # 输入每个分区的drop率（小数形式，0.3表示30%的标签会被保留）
    drop_rates = [0.3, 0.5, 0.2, 0.75]
    
    print(f"开始处理文件，输入目录: {input_directory}")
    print(f"输出目录: {output_directory}")
    print(f"使用的drop率列表: {drop_rates}")
    process_all_files(input_directory, output_directory, drop_rates)
    print("处理完成")
    