# dataset_tools
tools for dataset to train loras

正常流程：
- 使用两个downloader之一从pixiv拉取图片,如果只想要管图片，不从视频提取第一帧就用basic那个保险，如果要提取帧就用不带basic那个的，改一下设置
- 可选`ganther_children_folders_to_one_folder.py`把多个文件夹合到一个文件夹里，也可以不合
- 用`fill_img.py`把所有图片透明图层填充成白色
- 用`hash_to_delete.py`去重，一般阈值选10
- 用`delete_useless_txt.py`来把多出来的txt清理一下
- 用`tagger_api.py`给图片打标，部署的tagger是`https://github.com/spawner1145/wd14-inference-webui.git`这个项目或者webui的wd14插件，api填`https://127.0.0.1:7860/tagger/v1`这种
- 打完标以后用`check_matches.py`确认一下txt和img一一对应了
