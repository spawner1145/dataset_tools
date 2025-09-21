import requests
import base64
import json
from PIL import Image
from io import BytesIO
import os
import glob

class TaggerAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.interrogate_endpoint = f"{self.base_url}/interrogate"
        self.interrogators_endpoint = f"{self.base_url}/interrogators"
        
    def get_available_models(self):
        try:
            response = requests.get(self.interrogators_endpoint)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取模型列表失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应内容: {e.response.text}")
            return None
    
    def encode_image_to_base64(self, image_path: str) -> str:
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return img_str
        except Exception as e:
            print(f"图片编码失败: {str(e)}")
            return None
    
    def interrogate_image(self, 
                         image_path: str, 
                         model: str, 
                         threshold: float = 0.35,
                         character_threshold: float = 0.85,
                         general_mcut_enabled: bool = False,
                         character_mcut_enabled: bool = False):
        image_base64 = self.encode_image_to_base64(image_path)
        if not image_base64:
            return None
            
        payload = {
            "image": image_base64,
            "model": model,
            "threshold": threshold,
            "character_threshold": character_threshold,
            "general_mcut_enabled": general_mcut_enabled,
            "character_mcut_enabled": character_mcut_enabled
        }
        
        try:
            response = requests.post(
                self.interrogate_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"图片分析请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            return None

def process_tags(raw_tags, exclude_symbols, exclude_words):
    processed_tags = []
    for tag in raw_tags:
        if tag in exclude_words:
            continue
        if tag not in exclude_symbols:
            processed_tag = tag.replace('_', ' ')
            processed_tags.append(processed_tag)
        else:
            processed_tags.append(tag)
    
    return processed_tags

def save_tags_to_file(image_path, new_tags, fixed_prefix):
    txt_path = os.path.splitext(image_path)[0] + '.txt'
    
    existing_tags = []
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                # 处理带前缀的情况，移除前缀后再分割标签
                if fixed_prefix and content.startswith(fixed_prefix):
                    # 移除前缀
                    remaining_content = content[len(fixed_prefix):]
                    # 如果前缀后直接跟逗号，也一并移除
                    if remaining_content.startswith(','):
                        remaining_content = remaining_content[1:]
                    if remaining_content:
                        existing_tags = remaining_content.split(',')
                else:
                    existing_tags = content.split(',')
    
    tags_to_add = [tag for tag in new_tags if tag not in existing_tags]
    
    if tags_to_add or not os.path.exists(txt_path):
        all_tags = existing_tags + tags_to_add
        # 构建完整内容
        if fixed_prefix:
            if all_tags:
                # 前缀和标签之间添加逗号
                full_content = f"{fixed_prefix},{','.join(all_tags)}"
            else:
                # 只有前缀，没有标签
                full_content = fixed_prefix
        else:
            # 没有前缀的情况
            full_content = ','.join(all_tags) if all_tags else ''
            
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        if tags_to_add:
            print(f"已更新标签文件: {txt_path}")
            print(f"添加了 {len(tags_to_add)} 个新标签")
        else:
            if fixed_prefix:
                print(f"已创建标签文件并添加固定前缀: {txt_path}")
            else:
                print(f"已创建标签文件: {txt_path}")
    else:
        print(f"标签文件已存在且无新标签可添加: {txt_path}")

def main():
    API_BASE_URL = "https://u259632-be52-5d9841ca.bjc1.seetacloud.com:8443/tagger/v1"  # API服务地址
    IMAGE_FOLDER = "教義 Dogma 素材"                       # 图片文件夹路径
    MODEL_NAME = "wd14-eva02-large-v3-git"         # 要使用的模型名称
    THRESHOLD = 0.35                               # 通用标签阈值
    CHARACTER_THRESHOLD = 0.85                     # 角色标签阈值
    ENABLE_GENERAL_MCUT = False                    # 是否启用通用标签MCUT
    ENABLE_CHARACTER_MCUT = False                  # 是否启用角色标签MCUT
    LIST_MODELS_FIRST = False                      # 是否先列出所有模型
    FIXED_PREFIX = "<style>dogma</style>"        # 固定前缀（不带末尾逗号）
    #FIXED_PREFIX = ""
    # 若不需要前缀，可设置为：FIXED_PREFIX = ""
    
    EXCLUDE_SYMBOLS = {"0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", 
                      "<|>_<|>", "=_=", ">_<", "3_3", "6_9", ">_o", "@_@", 
                      "^_^", "o_o", "u_u", "x_x", "|_|", "||_||"}
    
    EXCLUDE_WORDS = {"general", "sensitive", "questionable", "explicit"}
    
    client = TaggerAPIClient(API_BASE_URL)
    
    if LIST_MODELS_FIRST:
        print("获取可用模型列表...")
        models_info = client.get_available_models()
        if models_info:
            print("\n可用模型:")
            for model_name in models_info['models']:
                info = models_info['model_info'][model_name]
                print(f"- {model_name}:")
                print(f"  仓库ID: {info['repo_id']}")
                print(f"  版本: {info['revision']}")
                print(f"  子文件夹: {info['subfolder'] or '无'}")
                print(f"  模型类型: {info['model_type']}")
    
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(IMAGE_FOLDER, ext)))
    
    if not image_files:
        print(f"在文件夹 {IMAGE_FOLDER} 中未找到任何图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件，开始处理...\n")
    
    for i, image_path in enumerate(image_files, 1):
        print(f"处理图片 {i}/{len(image_files)}: {os.path.basename(image_path)}")
        
        result = client.interrogate_image(
            image_path=image_path,
            model=MODEL_NAME,
            threshold=THRESHOLD,
            character_threshold=CHARACTER_THRESHOLD,
            general_mcut_enabled=ENABLE_GENERAL_MCUT,
            character_mcut_enabled=ENABLE_CHARACTER_MCUT
        )
        
        if result:
            raw_tags = list(result['caption'].keys())
            processed_tags = process_tags(raw_tags, EXCLUDE_SYMBOLS, EXCLUDE_WORDS)
            
            # 保存标签到文件
            save_tags_to_file(image_path, processed_tags, FIXED_PREFIX)
        else:
            print(f"图片 {image_path} 分析失败，跳过...")

if __name__ == "__main__":
    main()
    