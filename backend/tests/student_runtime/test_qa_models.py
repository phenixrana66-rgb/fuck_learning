import unittest

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from backend.chaoxing_db.models.qa import QAMessageAttachment


class QaModelSchemaTestCase(unittest.TestCase):
    def test_attachment_table_uses_mysql_unsigned_bigint_foreign_keys(self) -> None:
        ddl = str(CreateTable(QAMessageAttachment.__table__).compile(dialect=mysql.dialect()))

        self.assertIn("id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT", ddl)
        self.assertIn("message_id BIGINT UNSIGNED NOT NULL", ddl)
        self.assertIn("session_id BIGINT UNSIGNED NOT NULL", ddl)
        self.assertIn("lesson_id BIGINT UNSIGNED NOT NULL", ddl)
        self.assertIn("file_size BIGINT UNSIGNED", ddl)


if __name__ == "__main__":
    unittest.main()
