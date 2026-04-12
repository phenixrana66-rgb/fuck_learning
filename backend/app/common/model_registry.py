from backend.app.bootstrap import bootstrap_backend_common

bootstrap_backend_common()

import chaoxing_db.models  # noqa: F401
import backend.app.tasks.models  # noqa: F401
import backend.app.script.models  # noqa: F401
