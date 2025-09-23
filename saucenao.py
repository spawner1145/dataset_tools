import asyncio
import httpx
import json
import random
import urllib.parse
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Optional, Dict, List

# 需要保留下划线的特殊符号集合
EXCLUDE_SYMBOLS = {"0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", 
                   "<|>_<|>", "=_=", ">_<", "3_3", "6_9", ">_o", "@_@", 
                   "^_^", "o_o", "u_u", "x_x", "|_|", "||_||"}

def process_tags(tag_string: str) -> str:
    if not tag_string:
        return ""

    tags = tag_string.split(' ')
    processed_tags = []
    
    for tag in tags:
        if tag in EXCLUDE_SYMBOLS:
            processed_tags.append(tag)
        else:
            processed_tag = tag.replace('_', ' ')
            processed_tags.append(processed_tag)
    
    return ','.join(processed_tags)

def read_image_binary(image_path: str) -> bytes:
    try:
        with open(image_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"图片文件未找到：{image_path}")
    except Exception as e:
        raise Exception(f"读取图片失败：{str(e)}")

def get_random_api_key(api_key_list: List[str]) -> Optional[str]:
    valid_keys = [key.strip() for key in api_key_list if key.strip()]
    return random.choice(valid_keys) if valid_keys else None

# 索引配置
def get_db_bitmask():
    # 启用或禁用特定索引（1=启用，0=禁用）
    index_mangadex = '0'
    index_madokami = '0'
    index_pawoo = '0'
    index_da = '1'
    index_portalgraphics = '0'
    index_bcycosplay = '0'
    index_bcyillust = '0'
    index_idolcomplex = '0'
    index_e621 = '0'
    index_animepictures = '0'
    index_sankaku = '0'
    index_konachan = '0'
    index_gelbooru = '0'
    index_shows = '0'
    index_movies = '0'
    index_hanime = '0'
    index_anime = '0'
    index_medibang = '0'
    index_2dmarket = '0'
    index_hmisc = '0'
    index_fakku = '0'
    index_shutterstock = '0'
    index_reserved = '0'
    index_animeop = '0'
    index_yandere = '0'
    index_nijie = '1'
    index_drawr = '1'
    index_danbooru = '1'  # 启用Danbooru索引
    index_seigaillust = '1'
    index_pixivhistorical = '1'
    index_pixiv = '1'  # 启用Pixiv索引
    index_ddbsamples = '0'
    index_ddbobjects = '0'
    index_hcg = '0'
    index_hmags = '0'

    # 生成对应的位掩码
    bitmask_str = (
        index_mangadex + index_madokami + index_pawoo + index_da +
        index_portalgraphics + index_bcycosplay + index_bcyillust +
        index_idolcomplex + index_e621 + index_animepictures + index_sankaku +
        index_konachan + index_gelbooru + index_shows + index_movies +
        index_hanime + index_anime + index_medibang + index_2dmarket +
        index_hmisc + index_fakku + index_shutterstock + index_reserved +
        index_animeop + index_yandere + index_nijie + index_drawr +
        index_danbooru + index_seigaillust + index_anime + index_pixivhistorical +
        index_pixiv + index_ddbsamples + index_ddbobjects + index_hcg +
        index_hanime + index_hmags
    )
    return int(bitmask_str, 2)

async def fetch_saucenao(
    image_path: str,
    proxies: Optional[Dict[str, str]] = None,
    sauce_api_key_list: Optional[List[str]] = None
) -> str:
    api_key = get_random_api_key(sauce_api_key_list) if sauce_api_key_list else None
    use_api = api_key is not None
    
    params = {
        "output_type": "2" if use_api else "",
        "numres": "1",
        "minsim": SAUCE_MINSIM,
        "dbmask": get_db_bitmask(),
        "api_key": api_key if use_api else ""
    }
    
    url = "https://saucenao.com/search.php"
    image_data = read_image_binary(image_path)
    files = {"file": ("image.jpg", image_data, "image/jpeg")}
    
    for attempt in range(SAUCE_RETRY_MAX_ATTEMPTS):
        try:
            key_display = api_key if api_key else "未使用API"
            print(f"[SauceNAO] 当前模式：{'API调用' if use_api else '网页解析'}，Key：{key_display}")
            
            async with httpx.AsyncClient(
                timeout=SAUCE_TIMEOUT,
                proxies=proxies,
                follow_redirects=True
            ) as client:
                if use_api:
                    response = await client.post(url=url, params=params, files=files)
                else:
                    response = await client.post(url=url, files=files)
                
                response.raise_for_status()
                
                if use_api:
                    try:
                        results = response.json()

                        if results.get('header', {}).get('status') != 0:
                            raise Exception(f"API错误：{results.get('header', {}).get('message', '未知错误')}")

                        short_remaining = results.get('header', {}).get('short_remaining', 0)
                        long_remaining = results.get('header', {}).get('long_remaining', 0)
                        print(f"[SauceNAO] 剩余搜索次数：30秒内{short_remaining}次 | 24小时内{long_remaining}次")

                        if int(results.get('header', {}).get('results_returned', 0)) > 0:
                            first_result = results['results'][0]
                            similarity = float(first_result['header']['similarity'])

                            if similarity >= float(SAUCE_MINSIM.replace('!', '')):
                                if 'data' in first_result and 'ext_urls' in first_result['data']:
                                    for url in first_result['data']['ext_urls']:
                                        if "danbooru.donmai.us/post/show/" in url:
                                            return url.replace("danbooru.donmai.us", "kagamihara.donmai.us")
                            
                            print(f"[SauceNAO] 未找到达标结果（相似度：{similarity}%）")
                            return "danbooru无结果"
                        else:
                            print("[SauceNAO] 未返回任何结果")
                            return "danbooru无结果"
                            
                    except json.JSONDecodeError:
                        raise Exception("API返回非JSON格式数据")
                
                else:
                    soup = BeautifulSoup(response.text, "html.parser")
                    possible_links = []
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        if "danbooru.donmai.us/post/show/" in href:
                            possible_links.append(href)
                    
                    if not possible_links:
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            if "saucenao.com/search.php?db=999&url=" in href and "danbooru" in href:
                                possible_links.append(href)
                    
                    if possible_links:
                        first_link = possible_links[0]
                        if "danbooru.donmai.us/post/show/" in first_link:
                            return first_link.replace("danbooru.donmai.us", "kagamihara.donmai.us")
                        else:
                            parsed_url = urllib.parse.urlparse(first_link)
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            if "url" in query_params:
                                decoded_url = urllib.parse.unquote(query_params["url"][0])
                                if "danbooru.donmai.us/post/show/" in decoded_url:
                                    return decoded_url.replace("danbooru.donmai.us", "kagamihara.donmai.us")
                    
                    return "danbooru无结果"
                    
        except httpx.HTTPError as e:
            if "429" in str(e) and attempt < SAUCE_RETRY_MAX_ATTEMPTS - 1:
                if use_api and sauce_api_key_list:
                    api_key = get_random_api_key(sauce_api_key_list)
                    key_display = api_key if api_key else "未使用"
                    wait_time = SAUCE_RETRY_DELAY * (attempt + 1)
                    print(f"[SauceNAO] 请求频繁，{wait_time}秒后换Key重试（新Key：{key_display}，第{attempt+2}次）")
                else:
                    wait_time = SAUCE_RETRY_DELAY * (attempt + 1)
                    print(f"[SauceNAO] 请求频繁，{wait_time}秒后重试（第{attempt+2}次）")
                
                await asyncio.sleep(wait_time)
                continue
            if use_api and "403" in str(e):
                raise Exception("API Key无效或错误，请检查配置")
                
            raise Exception(f"请求SauceNAO失败：{str(e)}")
        except Exception as e:
            raise Exception(f"处理异常：{str(e)}")
    
    raise Exception(f"达到最大重试次数（{SAUCE_RETRY_MAX_ATTEMPTS}次），请求SauceNAO失败")

async def get_data_from_danbooru(
    post_url: str,
    proxies: Optional[Dict[str, str]] = None,
    danbooru_api_key_list: Optional[List[str]] = None
) -> Dict:
    if "kagamihara.donmai.us/post/show/" not in post_url:
        return {}

    post_id = post_url.split("/")[-1]
    if not post_id.isdigit():
        return {}

    api_key = get_random_api_key(danbooru_api_key_list) if danbooru_api_key_list else None
    use_api = api_key is not None
    api_url = f"https://kagamihara.donmai.us/posts/{post_id}.json"
    params = {"api_key": api_key} if use_api else {}
    
    for attempt in range(DANBOORU_RETRY_MAX_ATTEMPTS):
        try:
            key_display = api_key if api_key else "未使用API"
            print(f"[Danbooru] 当前模式：{'API调用' if use_api else '匿名访问'}，Key：{key_display}")
            
            async with httpx.AsyncClient(
                timeout=DANBOORU_TIMEOUT,
                proxies=proxies,
                follow_redirects=True
            ) as client:
                response = await client.get(api_url, params=params)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            if "429" in str(e) and attempt < DANBOORU_RETRY_MAX_ATTEMPTS - 1:
                if use_api and danbooru_api_key_list:
                    api_key = get_random_api_key(danbooru_api_key_list)
                    key_display = f"****{api_key[-4:]}" if api_key else "未使用"
                    wait_time = DANBOORU_RETRY_DELAY * (attempt + 1)
                    print(f"[Danbooru] 请求频繁，{wait_time}秒后换Key重试（新Key：{key_display}，第{attempt+2}次）")
                else:
                    wait_time = DANBOORU_RETRY_DELAY * (attempt + 1)
                    print(f"[Danbooru] 请求频繁，{wait_time}秒后重试（第{attempt+2}次）")
                
                await asyncio.sleep(wait_time)
                continue

            if use_api and "403" in str(e):
                raise Exception("Danbooru API Key无效或错误，请检查配置")
                
            raise Exception(f"请求Danbooru API失败：{str(e)}")
        except Exception as e:
            raise Exception(f"解析数据失败：{str(e)}")
    
    raise Exception(f"达到最大重试次数（{DANBOORU_RETRY_MAX_ATTEMPTS}次），请求Danbooru API失败")

async def process_single_image(
    image_path: str,
    output_format: str,
    proxies: Optional[Dict[str, str]] = None,
    save_file: bool = False,
    is_batch: bool = False,
    sauce_api_key_list: Optional[List[str]] = None,
    danbooru_api_key_list: Optional[List[str]] = None
) -> str:
    try:
        if is_batch:
            delay = random.uniform(MIN_REQUEST_INTERVAL, MAX_REQUEST_INTERVAL)
            print(f"等待 {delay:.2f} 秒后处理：{image_path}")
            await asyncio.sleep(delay)

        danbooru_url = await fetch_saucenao(
            image_path, 
            proxies, 
            sauce_api_key_list
        )
        print(f"处理图片: {image_path}")
        print(f"Danbooru链接：{danbooru_url}")
        
        if danbooru_url == "danbooru无结果":
            return "未找到相关数据"
            
        data = await get_data_from_danbooru(
            danbooru_url, 
            proxies, 
            danbooru_api_key_list
        )
        if not data:
            return "未找到有效数据"
        
        if output_format.lower() == "tag":
            tag_string = data.get('tag_string', '')
            result = process_tags(tag_string)
        elif output_format.lower() == "json":
            result = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return "不支持的输出格式，支持 'tag' 和 'json'"
        
        if save_file:
            file_path = Path(image_path)
            if output_format.lower() == "tag":
                output_path = file_path.with_suffix('.txt')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result)
            else:
                output_path = file_path.with_suffix('.json')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result)
            print(f"已保存结果到: {output_path}")
            
        return result
        
    except Exception as e:
        error_msg = f"处理失败：{str(e)}"
        print(error_msg)
        return error_msg

async def process_batch(
    folder_path: str,
    output_format: str,
    proxies: Optional[Dict[str, str]] = None,
    sauce_api_key_list: Optional[List[str]] = None,
    danbooru_api_key_list: Optional[List[str]] = None
) -> None:
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"错误：{folder_path} 不是有效的文件夹")
        return

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    image_files = [
        file for file in folder.iterdir() 
        if file.is_file() and file.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"在 {folder_path} 中未找到任何图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件，开始批量处理...")
    print(f"请求间隔：{MIN_REQUEST_INTERVAL}-{MAX_REQUEST_INTERVAL}秒")
    print(f"SauceNAO 配置：最小相似度{SAUCE_MINSIM}，重试{SAUCE_RETRY_MAX_ATTEMPTS}次/延迟{SAUCE_RETRY_DELAY}秒，API Key数量：{len([k for k in sauce_api_key_list if k.strip()]) if sauce_api_key_list else 0}")
    print(f"Danbooru 配置：重试{DANBOORU_RETRY_MAX_ATTEMPTS}次/延迟{DANBOORU_RETRY_DELAY}秒，API Key数量：{len([k for k in danbooru_api_key_list if k.strip()]) if danbooru_api_key_list else 0}")

    success_count = 0
    for i, file in enumerate(image_files, 1):
        print(f"\n处理第 {i}/{len(image_files)} 个文件")
        result = await process_single_image(
            str(file), 
            output_format, 
            proxies, 
            save_file=True,
            is_batch=True,
            sauce_api_key_list=sauce_api_key_list,
            danbooru_api_key_list=danbooru_api_key_list
        )
        
        if not result.startswith("处理失败") and result not in ["未找到相关数据", "未找到有效数据"]:
            success_count += 1
    
    print(f"\n批量处理完成：")
    print(f"总文件数：{len(image_files)}")
    print(f"成功处理：{success_count}")
    print(f"处理失败/无结果：{len(image_files) - success_count}")

async def main(
    target_path: str,
    output_format: str = "tag",
    batch: bool = False,
    proxies: Optional[Dict[str, str]] = None,
    sauce_api_key_list: Optional[List[str]] = None,
    danbooru_api_key_list: Optional[List[str]] = None
) -> None:
    target = Path(target_path)
    
    if batch:
        await process_batch(
            target_path, 
            output_format, 
            proxies, 
            sauce_api_key_list, 
            danbooru_api_key_list
        )
    else:
        if not target.is_file():
            print(f"错误：{target_path} 不是有效的文件")
            return
            
        result = await process_single_image(
            str(target), 
            output_format, 
            proxies, 
            save_file=False,
            sauce_api_key_list=sauce_api_key_list,
            danbooru_api_key_list=danbooru_api_key_list
        )
        print(f"处理结果：")
        print(result)

if __name__ == "__main__":
    # 通用配置
    TARGET_PATH = "test"  # 单个图片路径或文件夹路径
    OUTPUT_FORMAT = "json"  # 可选 "tag" 或 "json"
    IS_BATCH = True  # 批量处理：True(文件夹)/False(单文件)
    
    # 防429配置（API调用建议调大）
    MIN_REQUEST_INTERVAL = 3  # 最小请求间隔(秒)
    MAX_REQUEST_INTERVAL = 5  # 最大请求间隔(秒)
    
    # 代理配置
    USE_PROXIES = {
        "http://": "http://127.0.0.1:7890",
        "https://": "http://127.0.0.1:7890"
    }
    # USE_PROXIES = None  # 不使用代理时启用此行
    
    # API Key配置（支持多个，空值会自动过滤）
    SAUCE_API_KEY_LIST = [
        "",  # 空值会被跳过
        #"your_saucenao_api_key_here",  # 替换为你的SauceNAO API Key
    ]
    DANBOORU_API_KEY_LIST = [
        '',  # 空值会被跳过
        # "your_danbooru_api_key_here",  # 替换为你的Danbooru API Key
    ]

    # SauceNAO 配置
    SAUCE_MINSIM = "80!"  # 最小相似度，带!表示强制
    SAUCE_TIMEOUT = 30.0  # 超时时间(秒)
    SAUCE_RETRY_MAX_ATTEMPTS = 3  # 最大重试次数
    SAUCE_RETRY_DELAY = 30  # 基础重试延迟(秒)
    
    # Danbooru 配置
    DANBOORU_TIMEOUT = 30.0  # 超时时间(秒)
    DANBOORU_RETRY_MAX_ATTEMPTS = 3  # 最大重试次数
    DANBOORU_RETRY_DELAY = 10  # 基础重试延迟(秒)
    
    asyncio.run(
        main(
            TARGET_PATH, 
            OUTPUT_FORMAT, 
            IS_BATCH, 
            USE_PROXIES,
            sauce_api_key_list=SAUCE_API_KEY_LIST,
            danbooru_api_key_list=DANBOORU_API_KEY_LIST
        )
    )
