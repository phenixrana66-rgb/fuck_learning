CREATE TABLE IF NOT EXISTS qa_faq_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    category VARCHAR(128) NULL,
    canonical_question VARCHAR(512) NOT NULL,
    answer_text TEXT NOT NULL,
    match_mode VARCHAR(64) NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'enabled',
    source VARCHAR(64) NOT NULL DEFAULT 'organizer_dataset',
    source_file VARCHAR(255) NULL,
    source_sheet VARCHAR(128) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS qa_faq_variants (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    faq_item_id BIGINT UNSIGNED NOT NULL,
    variant_text VARCHAR(512) NOT NULL,
    variant_type VARCHAR(32) NOT NULL,
    sort_no INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_qa_faq_variants_faq_item
        FOREIGN KEY (faq_item_id) REFERENCES qa_faq_items(id)
);

CREATE TABLE IF NOT EXISTS qa_answer_traces (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id BIGINT UNSIGNED NULL,
    question_message_id BIGINT UNSIGNED NULL,
    answer_message_id BIGINT UNSIGNED NULL,
    lesson_id BIGINT UNSIGNED NULL,
    section_id BIGINT UNSIGNED NULL,
    page_no INTEGER NULL,
    model_provider VARCHAR(64) NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    embedding_model VARCHAR(128) NULL,
    faq_hit_ids_json JSON NULL,
    context_chunk_ids_json JSON NULL,
    prompt_version VARCHAR(64) NULL,
    latency_ms INTEGER NULL,
    confidence_score FLOAT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_qa_answer_traces_session
        FOREIGN KEY (session_id) REFERENCES qa_sessions(id),
    CONSTRAINT fk_qa_answer_traces_question_message
        FOREIGN KEY (question_message_id) REFERENCES qa_messages(id),
    CONSTRAINT fk_qa_answer_traces_answer_message
        FOREIGN KEY (answer_message_id) REFERENCES qa_messages(id),
    CONSTRAINT fk_qa_answer_traces_lesson
        FOREIGN KEY (lesson_id) REFERENCES lessons(id),
    CONSTRAINT fk_qa_answer_traces_section
        FOREIGN KEY (section_id) REFERENCES lesson_sections(id)
);
