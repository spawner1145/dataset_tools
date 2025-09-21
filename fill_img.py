from PIL import Image
import os

def fill_transparent_with_white(image_path, output_path):
    """将图像中的透明部分填充为白色"""
    try:
        img = Image.open(image_path).convert("RGBA")
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        result = Image.alpha_composite(white_bg, img)
        result = result.convert("RGB")
        result.save(output_path)
        return True
    except Exception as e:
        print(f"处理文件 {image_path} 时出错: {str(e)}")
        return False

def process_folder(input_folder, output_folder=None):
    # 如果未指定输出文件夹，则在输入文件夹下创建一个output子文件夹
    if output_folder is None:
        output_folder = os.path.join(input_folder, "output")
    
    # 创建输出文件夹（如果不存在）
    os.makedirs(output_folder, exist_ok=True)
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    
    # 遍历文件夹中的所有文件
    for filename in os.listdir(input_folder):
        # 检查文件扩展名是否为图像
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            if fill_transparent_with_white(input_path, output_path):
                print(f"已处理: {filename}")

if __name__ == "__main__":
    input_folder = "emilia"  # 替换为你的文件夹路径
    
    process_folder(input_folder)
    print("处理完成！处理后的文件保存在输入文件夹的output子文件夹中。")
