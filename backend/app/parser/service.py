from pathlib import PurePosixPath

from backend.app.parser.schemas import FileInfo, PreviewChapter, PreviewSubChapter, StructurePreview


def build_file_info(file_url: str, file_type: str) -> FileInfo:
    suffix = PurePosixPath(file_url).name or f"courseware.{file_type}"
    page_count = 12 if file_type == "ppt" else 18
    return FileInfo(
        fileName=suffix,
        fileSize=2_048_000,
        pageCount=page_count,
    )


def build_structure_preview(course_id: str) -> StructurePreview:
    return StructurePreview(
        chapters=[
            PreviewChapter(
                chapterId=f"{course_id}-chap-001",
                chapterName="课程导入与核心问题",
                subChapters=[
                    PreviewSubChapter(
                        subChapterId=f"{course_id}-sub-001",
                        subChapterName="基础概念引入",
                        pageRange="1-3",
                    ),
                    PreviewSubChapter(
                        subChapterId=f"{course_id}-sub-002",
                        subChapterName="关键概念展开",
                        pageRange="4-7",
                    ),
                ],
            ),
            PreviewChapter(
                chapterId=f"{course_id}-chap-002",
                chapterName="案例与总结",
                subChapters=[
                    PreviewSubChapter(
                        subChapterId=f"{course_id}-sub-003",
                        subChapterName="案例分析",
                        pageRange="8-10",
                    ),
                    PreviewSubChapter(
                        subChapterId=f"{course_id}-sub-004",
                        subChapterName="小结与练习",
                        pageRange="11-12",
                    ),
                ],
            ),
        ]
    )
