import sys
from pathlib import Path

# 将后端目录添加到 Python 路径中以防导入失败
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from backend.app.common.storage import get_storage_manager
from backend.app.lesson.voice_storage import save_audio_file, build_voice_public_url
from backend.app.student_runtime.qa_image_storage import store_qa_image_from_data_url, load_qa_image_as_data_url

def test_s3_components():
    print("====== 开始文件存储测试 ======")
    
    # 1. 测试基础 storage_manager
    print("\n1. 测试 StorageManager...")
    sm = get_storage_manager()
    print(f"当前选用的 StorageProvider: {sm.__class__.__name__}")
    
    test_bytes = b"Hello MinIO S3! This is a test file for antigravity."
    test_key = "tests/hello_s3.txt"
    
    print(f"上传二进制数据到 '{test_key}'...")
    url = sm.upload_bytes(test_bytes, test_key, content_type="text/plain")
    print(f"成功上传，返回的 URL 为: {url}")
    
    print("重新下载数据以验证一致性...")
    downloaded = sm.download_bytes(test_key)
    print(f"下载的数据内容: {downloaded.decode('utf-8')}")
    assert downloaded == test_bytes, "数据不匹配！"
    print("S3 基础读写测试通过！")
    
    # 2. 测试音频模块
    print("\n2. 测试音频模块...")
    audio_data = b"MOCK_MP3_DATA_FOR_TESTING"
    stored_audio = save_audio_file(audio_data, "mp3", filename_prefix="hello-test")
    print(f"生成音频文件名: {stored_audio.filename}")
    print(f"音频大小: {stored_audio.file_size} 字节")
    
    audio_url = build_voice_public_url(stored_audio.filename)
    print(f"生成的音频公共访问 URL: {audio_url}")
    
    audio_content = sm.download_bytes(f"voice/{stored_audio.filename}")
    assert audio_content == audio_data, "音频数据一致性校验失败！"
    print("音频模块测试通过！")
    
    # 3. 测试 Q&A 图片模块
    print("\n3. 测试 Q&A 图片模块...")
    # 一张极小的红色 1x1 像素 GIF 的 base64 编码
    base64_gif = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    
    print("保存 Base64 图片到存储...")
    stored_img = store_qa_image_from_data_url(data_url=base64_gif)
    print(f"保存成功，存储提供商: {stored_img.storage_provider}, 存储 Key: {stored_img.storage_key}")
    print(f"图片公共访问 URL: {stored_img.url}")
    
    print("再次从存储加载为 Base64...")
    loaded_base64 = load_qa_image_as_data_url(stored_img.storage_key, mime_type=stored_img.mime_type)
    print(f"原始 Base64: {base64_gif[:60]}...")
    print(f"读取 Base64: {loaded_base64[:60]}...")
    assert loaded_base64.split(",")[-1] == base64_gif.split(",")[-1], "Base64 数据读取不一致！"
    print("Q&A 图片模块测试通过！")
    
    print("\n====== 所有文件存储组件测试全部通过！ ======")

if __name__ == "__main__":
    try:
        test_s3_components()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
