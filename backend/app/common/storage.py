from abc import ABC, abstractmethod
from io import BytesIO
import json
import logging
from pathlib import Path
from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, local_path: Path, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        """上传本地 file 到存储，返回可访问的 URL"""
        pass

    @abstractmethod
    def upload_bytes(self, data: bytes, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        """上传二进制字节流到存储，返回可访问的 URL"""
        pass

    @abstractmethod
    def download_bytes(self, storage_key: str, bucket: str | None = None) -> bytes:
        """从存储下载二进制数据"""
        pass

    @abstractmethod
    def get_public_url(self, storage_key: str, bucket: str | None = None, base_url: str | None = None) -> str:
        """获取资源的公共访问 URL"""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]

    def _resolve_local_path(self, storage_key: str) -> tuple[Path, str]:
        # 逻辑映射：剥离首层前缀映射到本地目录，以向后兼容本地挂载路由
        parts = storage_key.split("/", 1)
        if len(parts) < 2:
            raise ApiError(400, f"无效的存储键值格式: {storage_key}")
        
        prefix, sub_key = parts[0], parts[1]
        if prefix == "courseware":
            local_dir = self.project_root / "public" / "courseware-previews"
            public_route = "/courseware-previews"
        elif prefix == "voice":
            from backend.app.lesson.voice_storage import get_voice_cache_dir
            local_dir = get_voice_cache_dir()
            public_route = "/cache/voice"
        elif prefix == "qa":
            from backend.app.student_runtime.qa_image_storage import get_qa_image_cache_dir
            local_dir = get_qa_image_cache_dir()
            public_route = "/cache/qa-images"
        else:
            local_dir = self.project_root / "cache" / "others"
            public_route = "/cache/others"
            
        target_path = local_dir / sub_key
        public_url = f"{public_route}/{sub_key.replace('\\\\', '/').strip('/')}"
        return target_path, public_url

    def upload_file(self, local_path: Path, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        target_path, public_url = self._resolve_local_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        try:
            shutil.copy2(local_path, target_path)
            return public_url
        except Exception as e:
            raise ApiError(500, f"本地拷贝文件失败: {e}") from e

    def upload_bytes(self, data: bytes, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        target_path, public_url = self._resolve_local_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            target_path.write_bytes(data)
            return public_url
        except Exception as e:
            raise ApiError(500, f"写入本地数据失败: {e}") from e

    def download_bytes(self, storage_key: str, bucket: str | None = None) -> bytes:
        target_path, _ = self._resolve_local_path(storage_key)
        if not target_path.exists():
            raise ApiError(404, f"文件未找到: {storage_key}")
        try:
            return target_path.read_bytes()
        except Exception as e:
            raise ApiError(500, f"读取本地文件失败: {e}") from e

    def get_public_url(self, storage_key: str, bucket: str | None = None, base_url: str | None = None) -> str:
        _, public_url = self._resolve_local_path(storage_key)
        if base_url:
            from urllib.parse import urljoin
            normalized_base = base_url.rstrip("/") + "/"
            return urljoin(normalized_base, public_url.lstrip("/"))
        return public_url


class MinioStorageProvider(StorageProvider):
    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.s3_endpoint
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.secure = settings.s3_secure
        self.default_bucket = settings.s3_bucket
        self.public_url_prefix = settings.s3_public_url.rstrip("/")

        from minio import Minio
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            # 自动初始化默认桶
            self._ensure_bucket(self.default_bucket)
        except Exception as e:
            logging.error(f"初始化 MinIO 客户端失败: {e}")
            self.client = None

    def _ensure_bucket(self, bucket: str):
        if not self.client:
            return
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                # 设置全局匿名只读 Policy，使前端能直接加载图片与音频
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }
                    ]
                }
                self.client.set_bucket_policy(bucket, json.dumps(policy))
        except Exception as e:
            logging.error(f"检查/自动创建 MinIO 桶 '{bucket}' 失败: {e}")

    def upload_file(self, local_path: Path, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        if not self.client:
            raise ApiError(500, "MinIO 客户端未初始化")
        
        bucket_name = bucket or self.default_bucket
        self._ensure_bucket(bucket_name)
        
        key = storage_key.replace("\\", "/").strip("/")
        try:
            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=key,
                file_path=str(local_path),
                content_type=content_type or "application/octet-stream"
            )
            return self.get_public_url(key, bucket_name)
        except Exception as e:
            raise ApiError(500, f"上传本地文件至 MinIO 失败: {e}") from e

    def upload_bytes(self, data: bytes, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        if not self.client:
            raise ApiError(500, "MinIO 客户端未初始化")
        
        bucket_name = bucket or self.default_bucket
        self._ensure_bucket(bucket_name)
        
        key = storage_key.replace("\\", "/").strip("/")
        try:
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=key,
                data=BytesIO(data),
                length=len(data),
                content_type=content_type or "application/octet-stream"
            )
            return self.get_public_url(key, bucket_name)
        except Exception as e:
            raise ApiError(500, f"上传数据字节至 MinIO 失败: {e}") from e

    def download_bytes(self, storage_key: str, bucket: str | None = None) -> bytes:
        if not self.client:
            raise ApiError(500, "MinIO 客户端未初始化")
        
        bucket_name = bucket or self.default_bucket
        key = storage_key.replace("\\", "/").strip("/")
        try:
            response = self.client.get_object(bucket_name, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            raise ApiError(500, f"从 MinIO 下载数据失败: {e}") from e

    def get_public_url(self, storage_key: str, bucket: str | None = None, base_url: str | None = None) -> str:
        del base_url
        bucket_name = bucket or self.default_bucket
        key = storage_key.replace("\\", "/").strip("/")
        
        if bucket_name == self.default_bucket and self.public_url_prefix:
            return f"{self.public_url_prefix}/{key}"
            
        schema = "https://" if self.secure else "http://"
        return f"{schema}{self.endpoint}/{bucket_name}/{key}"


_storage_manager: StorageProvider | None = None

def get_storage_manager() -> StorageProvider:
    global _storage_manager
    if _storage_manager is None:
        settings = get_settings()
        if settings.s3_enabled:
            _storage_manager = MinioStorageProvider()
        else:
            _storage_manager = LocalStorageProvider()
    return _storage_manager
