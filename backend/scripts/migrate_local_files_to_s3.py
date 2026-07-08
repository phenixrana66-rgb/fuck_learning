import sys
import os
import json
from pathlib import Path
from urllib.parse import unquote

# 将后端目录添加到 Python 路径中以防导入失败
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from backend.app.common.db import session_scope
from backend.app.common.storage import get_storage_manager
from backend.chaoxing_db.models import ChapterSectionAudioAsset, ChapterAudioAsset, ChapterParseTask
from backend.chaoxing_db.models.qa import QAMessageAttachment

def migrate_to_s3():
    print("====== 开始本地文件到 MinIO S3 的数据迁移 ======")
    sm = get_storage_manager()
    print(f"当前存储提供者: {sm.__class__.__name__}")
    
    if sm.__class__.__name__ == "LocalStorageProvider":
        print("错误: 当前 s3_enabled 为 False，未启用 S3 存储，请先在 config.local.py 中配置并启用 s3_enabled = True 后再运行迁移！")
        return

    # 1. 迁移音频文件
    print("\n1. 正在扫描并迁移音频文件...")
    with session_scope() as db:
        # 小节音频
        section_audios = db.query(ChapterSectionAudioAsset).filter(
            ChapterSectionAudioAsset.audio_url.like("%/cache/voice/%")
        ).all()
        print(f"找到待迁移的小节音频记录: {len(section_audios)} 条")
        
        section_migrated = 0
        for audio in section_audios:
            # 提取文件名
            filename = unquote(audio.audio_url.split("/")[-1])
            local_path = project_root / "cache" / "voice" / filename
            
            if local_path.exists():
                storage_key = f"voice/{filename}"
                print(f"  -> 上传音频: {filename}...")
                s3_url = sm.upload_file(local_path, storage_key, content_type=f"audio/{audio.audio_format.lower()}")
                
                # 更新数据库
                audio.audio_url = s3_url
                section_migrated += 1
            else:
                print(f"  [警告] 本地文件未找到: {local_path}，跳过上传，但保留数据库原状")
                
        # 主音频
        main_audios = db.query(ChapterAudioAsset).filter(
            ChapterAudioAsset.audio_url.like("%/cache/voice/%")
        ).all()
        print(f"找到待迁移的主音频记录: {len(main_audios)} 条")
        
        main_migrated = 0
        for audio in main_audios:
            filename = unquote(audio.audio_url.split("/")[-1])
            local_path = project_root / "cache" / "voice" / filename
            
            if local_path.exists():
                storage_key = f"voice/{filename}"
                print(f"  -> 上传主音频: {filename}...")
                s3_url = sm.upload_file(local_path, storage_key, content_type=f"audio/{audio.audio_format.lower()}")
                
                audio.audio_url = s3_url
                main_migrated += 1
            else:
                print(f"  [警告] 本地文件未找到: {local_path}，跳过上传")

        print(f"音频迁移完毕。共更新数据库记录: 小节音频 {section_migrated} 条，主音频 {main_migrated} 条。")

    # 2. 迁移 Q&A 图片文件
    print("\n2. 正在扫描并迁移学生端问答图片...")
    with session_scope() as db:
        attachments = db.query(QAMessageAttachment).filter(
            QAMessageAttachment.storage_provider == "local"
        ).all()
        print(f"找到待迁移的 Q&A 本地图片记录: {len(attachments)} 条")
        
        qa_migrated = 0
        for att in attachments:
            storage_key = att.storage_key  # 例如 'xx/xxxx.png'
            local_path = project_root / "cache" / "qa-images" / storage_key
            
            if local_path.exists():
                full_storage_key = f"qa/{storage_key}"
                print(f"  -> 上传图片: {storage_key}...")
                
                # 推测 MIME 类型
                import mimetypes
                mime_type = mimetypes.guess_type(local_path.name)[0] or "image/jpeg"
                s3_url = sm.upload_file(local_path, full_storage_key, content_type=mime_type)
                
                # 更新数据库
                att.storage_provider = "s3"
                att.file_url = s3_url
                qa_migrated += 1
            else:
                print(f"  [警告] 本地图片未找到: {local_path}，跳过上传")
                
        print(f"问答图片迁移完毕。共更新数据库记录: {qa_migrated} 条。")

    # 3. 迁移老课件预览图片 (物理文件迁移)
    print("\n3. 正在扫描并物理迁移老课件页预览图...")
    previews_dir = project_root / "public" / "courseware-previews"
    courseware_migrated_files = 0
    
    if previews_dir.exists():
        # 遍历 public/courseware-previews/ 下的每个 parse_id 目录
        for parse_id_dir in previews_dir.iterdir():
            if parse_id_dir.is_dir():
                parse_id = parse_id_dir.name
                print(f"  正在迁移课件解析 ID '{parse_id}' 的预览图...")
                
                # 遍历该目录下的图片页
                for img_path in parse_id_dir.glob("page-*.png"):
                    img_name = img_path.name
                    storage_key = f"courseware/{parse_id}/{img_name}"
                    
                    print(f"    -> 上传预览页: {img_name}...")
                    sm.upload_file(img_path, storage_key, content_type="image/png")
                    courseware_migrated_files += 1
                    
        print(f"老课件页预览图物理迁移完毕。共上传物理图片 {courseware_migrated_files} 张。")
    else:
        print("本地不存在老课件预览图目录，跳过物理文件迁移。")

    print("\n====== 数据迁移圆满结束！ ======")

if __name__ == "__main__":
    migrate_to_s3()
