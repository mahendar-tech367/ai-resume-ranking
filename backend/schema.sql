-- ==========================================
-- ResumeRanker PostgreSQL Database Schema
-- ==========================================

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,

    username VARCHAR(100) UNIQUE NOT NULL,

    email VARCHAR(255) UNIQUE,

    password TEXT NOT NULL,

    role VARCHAR(20) DEFAULT 'user',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- RESUMES TABLE
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,

    filename VARCHAR(255) NOT NULL,

    file_path TEXT,

    extracted_text TEXT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_resume_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- RANKING RESULTS TABLE
CREATE TABLE IF NOT EXISTS ranking_results (
    id SERIAL PRIMARY KEY,

    resume_id INTEGER NOT NULL,

    user_id INTEGER NOT NULL,

    score NUMERIC(5, 2),

    rank_position INTEGER,

    matched_keywords TEXT,

    missing_keywords TEXT,

    analysis TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_result_resume
        FOREIGN KEY (resume_id)
        REFERENCES resumes(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_result_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- AI CHAT HISTORY TABLE
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,

    user_id INTEGER,

    message TEXT NOT NULL,

    response TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


-- USEFUL INDEXES
CREATE INDEX IF NOT EXISTS idx_resumes_user_id
ON resumes(user_id);

CREATE INDEX IF NOT EXISTS idx_results_user_id
ON ranking_results(user_id);

CREATE INDEX IF NOT EXISTS idx_chat_user_id
ON chat_messages(user_id);