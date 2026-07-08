# MinIO S3 存储改造与系统稳定性优化方案

本方案旨在为“AI互动智课后端服务”提供稳定、可拔插的 MinIO S3 存储支持，解决当前系统在文件存储上的不稳定隐患，并设计高扩展性的文件管理模块。

---

## 1. 当前文件存储不稳定问题调查

经过对后端代码的调查，目前系统在文件存储上无法稳定使用，主要存在以下几个问题：

1. **Windows 环境下的临时路径 Bug (`pptx_reader.py`)**  
   在 `backend/app/parser/pptx_reader.py` 的第 147 行中：
   ```python
   with tempfile.TemporaryDirectory(prefix="pptx-preview-", dir="/tmp") as temp_dir_name:
   ```
   代码中硬编码了临时目录为 `/tmp`。由于当前开发与运行环境是 Windows 系统，`/tmp` 目录在 Windows 下并不默认存在。因此，当调用 PowerPoint 转换课件（PPTX）为预览图时，会因为“找不到指定的路径：`/tmp`”而直接抛出异常导致课件解析失败。这是导致文件存储无法稳定使用的**致命隐患**。
   
2. **业务逻辑与本地文件系统高度耦合（缺乏存储抽象）**  
   系统中有三处核心的文件存储需求：
   * **课件预览图**：直接在 `pptx_reader.py` 和 `pdf_reader.py` 中写本地 `public/courseware-previews/` 目录。
   * **交互音频（TTS及录音）**：直接在 `voice_storage.py` 中写本地 `cache/voice/` 目录。
   * **学生提问/大模型生成图片**：直接在 `qa_image_storage.py` 中写本地 `cache/qa-images/` 目录。
   
   各模块均使用 Python 内置的 `Path.write_bytes` 或 `shutil.copy` 直接操作本地磁盘，没有统一的存储管理层。若直接修改它们来对接 S3 接口，会导致多处代码重复编写，逻辑混乱。

3. **缺乏多节点/分布式部署支持**  
   若未来系统进行多节点容器化部署或前后端物理分离部署，由于图片和音频都保存在某一台机器的本地磁盘上，其他节点将无法访问 these 资源，从而导致前端加载 404 或解析异常。

---

## 2. 存储桶（Bucket）实现方案对比

用户提到：“s3 已经创建 存储桶 `chaoxing`，也许一个桶不是很好，请你考虑具体的实现方案。”  
为了实现良好的资源隔离与权限控制，我们对比以下两种存储桶设计方案：

### 方案 A：单桶多前缀（逻辑隔离）——【推荐】
继续使用已创建的 `chaoxing` 存储桶，通过**逻辑路径前缀**进行不同业务文件的隔离：
* 课件预览图：`chaoxing/courseware/{parse_id}/page-{index}.png`
* 交互音频：`chaoxing/voice/{filename}`
* 学生问答图片：`chaoxing/qa/{storage_key}`

*   **优点**：
    1. **运维极简**：只需在 MinIO 中维护一个 `chaoxing` 桶。
    2. **配置简单**：后端仅需配置一个桶名即可。
    3. **权限控制灵活**：MinIO 能够配置前缀级别的 Policy。例如，可以将 `courseware/*` 和 `voice/*` 路径配置为匿名可读（Public Read），而将 `qa/*` 配置为私有（Private），由后端生成 Presigned URL 进行受控访问。
*   **缺点**：在物理上所有业务的文件仍然在同一个 Bucket 中。

### 方案 B：多桶隔离（物理隔离）
为不同的业务模块创建专用的 Bucket：
* 课件预览图 Bucket：`chaoxing-courseware`（公共可读）
* 交互音频 Bucket：`chaoxing-voice`（公共可读）
* 学生提问/问答图片 Bucket：`chaoxing-qa`（私有，使用 Presigned URL）

*   **优点**：
    1. **物理安全隔离**：不同业务文件完全存放在不同的存储空间中，误操作风险低。
    2. **生命周期（Lifecycle）管理方便**：可以对不同桶单独设置过期清理策略（例如 `chaoxing-qa` 里的临时答题图 7 天自动删除，而 `chaoxing-courseware` 永久保存）。
*   **缺点**：
    1. 需要在 MinIO 控制台提前创建多个存储桶。
    2. 后端配置文件中需要维护多个存储桶名称。

### 💡 权衡与选择
**我们建议采用“方案 A（单桶多前缀）”作为默认推荐方案**，以保持最简的部署成本。但在**存储管理器代码设计上，我们会支持传入自定义的 Bucket**。这样如果后续需要过渡到方案 B，仅需在配置文件中将各业务的 Bucket 配置为不同的名称即可，无需修改任何业务代码。

---

## 3. 改造方案详细设计

我们将引入一个统一的存储管理器（`StorageManager`），它支持**本地文件存储**与**S3 (MinIO) 存储**的双重实现，并通过配置（`s3_enabled`）实现无缝切换。

### 3.1 新增配置参数 (`config.py`)
在 `backend/app/common/config.py` 的 `Settings` 模型中新增以下字段：

```python
# ====================== S3 / MinIO 存储配置 ======================
s3_enabled: bool = False
s3_endpoint: str = "localhost:13052"
s3_access_key: str = "zero"
s3_secret_key: str = "zKV;jkO|&&T!qz0Ou0Yq:Ycf"
s3_secure: bool = False  # 是否启用 HTTPS 证书校验
s3_bucket: str = "chaoxing"
s3_public_url: str = "http://localhost:13052/chaoxing"  # 对外消费的 URL 前缀
```

> [!IMPORTANT]
> 对外消费的 `s3_public_url` 与 `s3_endpoint` 分离设计。因为在内网开发中，后端服务器连接 MinIO 可以使用内网 IP（如 `127.0.0.1:13052`），但学生端/前端在浏览器里消费图片时，可能需要使用宿主机 IP（如 `http://192.168.x.x:13052/chaoxing`），分离设计可以确保多网络环境下正常工作。

### 3.2 抽象存储管理器设计 (`storage.py`)
在 `backend/app/common/storage.py` 中实现存储适配器模式：

```python
from abc import ABC, abstractmethod
from pathlib import Path

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, local_path: Path, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        """上传本地文件到存储，返回可访问的 URL"""
        pass

    @abstractmethod
    def upload_bytes(self, data: bytes, storage_key: str, bucket: str | None = None, content_type: str | None = None) -> str:
        """上传二进制字节流到存储，返回可访问 the URL"""
        pass

    @abstractmethod
    def download_bytes(self, storage_key: str, bucket: str | None = None) -> bytes:
        """从存储下载二进制数据"""
        pass

    @abstractmethod
    def get_public_url(self, storage_key: str, bucket: str | None = None) -> str:
        """获取资源的公共访问 URL"""
        pass
```

我们会分别实现：
1. `LocalStorageProvider`：若 `s3_enabled = False`，将文件写入本地 `public` 文件夹下，返回以 `/` 开头的相对 URL（与原系统一致）。
2. `MinioStorageProvider`：若 `s3_enabled = True`，使用官方 `minio` Python SDK 上传到 MinIO 中，并返回以 `s3_public_url` 为前缀的绝对 URL。

同时，我们通过工厂函数提供一个全局单例 `storage_manager`：
```python
_storage_manager: StorageProvider | None = None

def get_storage_manager() -> StorageProvider:
    global _storage_manager
    # 根据 settings.s3_enabled 懒加载并实例化对应的 Provider
    ...
```

### 3.3 各业务模块接入方案

#### 3.3.1 课件解析图导出改造 (`pptx_reader.py` / `pdf_reader.py`)
1. **修复临时路径**：将 `tempfile.TemporaryDirectory(prefix="pptx-preview-", dir="/tmp")` 中的 `dir="/tmp"` 移除（或者设为 `None`），使其自动使用系统自带的临时路径。
2. **上传到存储**：在 `_build_preview_urls` 导出单页 PNG 后：
   - 之前：`shutil.copy2(source_path, target_path)` 拷贝到本地 `public/courseware-previews`。
   - 之后：调用 `storage_manager.upload_file(source_path, f"courseware/{parse_id}/page-{index}.png")` 上传。
   - `preview_urls[index]` 记录为 `storage_manager` 返回的 URL。
3. 课件解析相关的数据表（`ChapterParseResult`、`ChapterPptAsset`）中的地址字段将无缝存储为 S3 绝对 URL（如启用了 S3）或本地相对路径（如未启用）。

#### 3.3.2 交互音频存储改造 (`voice_storage.py`)
1. 修改 `save_audio_file(audio_bytes, audio_format, ...)`：
   - 不再本地创建 `cache/voice` 目录和写盘。
   - 计算文件名后，调用 `storage_manager.upload_bytes(audio_bytes, f"voice/{filename}", content_type=f"audio/{audio_format}")` 上传。
   - 返回 `StoredAudioFile(filename=filename, path=None, file_size=len(audio_bytes))`。
2. 修改 `build_voice_public_url`：
   - 直接调用 `storage_manager.get_public_url(f"voice/{filename}")` 获得可供前端直接播放的 URL。

#### 3.3.3 学生端问答图片存储改造 (`qa_image_storage.py`)
1. 修改 `store_qa_image_from_data_url` 和 `store_qa_image_from_url`：
   - 不再将字节写入本地 `cache/qa-images`。
   - 调用 `storage_manager.upload_bytes(raw_bytes, f"qa/{storage_key}", content_type=resolved_mime)` 进行上传。
2. 修改 `load_qa_image_as_data_url(storage_key: str, ...)`：
   - 当大模型端需要将提问图片读取为 Base64 传递给多模态 LLM 时，调用 `storage_manager.download_bytes(f"qa/{storage_key}")` 获取图片字节，再做 Base64 编码。
   - 这样既保证了大模型端能够正常拿到图片字节，又让前端直接使用 S3 的图片 URL 渲染，极大降低了本地缓存占用。

---

## 4. 实施计划

1. **第一步：基础架构支持与配置**  
   * 修改 `backend/app/common/config.py`，新增 MinIO/S3 相关的配置项，并在本地 `config.local.py` 中补充连接凭证。
   * 新建 `backend/app/common/storage.py` 文件，实现 `LocalStorageProvider` 和 `MinioStorageProvider`，编写自动初始化 Bucket 的逻辑。
2. **第二步：修复 PPT 解析的 Windows 路径 Bug**  
   * 移除 `pptx_reader.py` 中的 `dir="/tmp"` 限制，保证解析可在 Windows 下稳定调起。
3. **第三步：改造课件解析模块**  
   * 改造 `pptx_reader.py` 的预览图生成逻辑，使其支持通过 `storage_manager` 上传。
4. **第四步：改造音频模块与 Q&A 图片模块**  
   * 将 `voice_storage.py` 和 `qa_image_storage.py` 改造为调用 `storage_manager`。
5. **第五步：系统测试与验证**  
   * 编写一个小测试脚本测试课件解析、音频生成、Q&A 存取在 `s3_enabled=True` 和 `False` 两种情况下的稳定性。
