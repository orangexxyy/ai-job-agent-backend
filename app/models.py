CANDIDATE_PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS candidate_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    expected_salary_min INTEGER,
    expected_salary_max INTEGER,
    minimum_salary INTEGER,
    salary_note TEXT,
    availability_note TEXT,
    preferred_cities TEXT,
    acceptable_cities TEXT,
    relocation_policy TEXT,
    outsourcing_policy TEXT,
    onsite_policy TEXT,
    remote_policy TEXT,
    overtime_policy TEXT,
    business_trip_policy TEXT,
    target_roles TEXT,
    available_projects TEXT,
    truth_boundaries TEXT,
    resume_text TEXT,
    project_context TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


APPLICATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_source TEXT,
    job_url TEXT,
    jd_text TEXT,
    status TEXT NOT NULL,
    match_score INTEGER,
    hr_contact_name TEXT,
    hr_contact_channel TEXT,
    last_hr_message TEXT,
    next_action TEXT,
    next_action_due_date TEXT,
    notes TEXT,
    risk_flags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


INTERVIEW_AVAILABILITY_SLOTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS interview_availability_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


APPLICATION_ACTION_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS application_action_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER,
    action_type TEXT NOT NULL,
    action_source TEXT NOT NULL,
    before_status TEXT,
    after_status TEXT,
    before_next_action TEXT,
    after_next_action TEXT,
    user_confirmed INTEGER NOT NULL,
    external_action_performed INTEGER NOT NULL,
    risk_level TEXT,
    summary TEXT NOT NULL,
    detail_json TEXT,
    created_at TEXT NOT NULL
);
"""


APPLICATION_ACTION_HISTORY_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_application_action_history_application_id_id
ON application_action_history (application_id, id DESC);
"""


PROFILE_APPLY_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profile_apply_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_path TEXT NOT NULL,
    backup_path TEXT,
    profile_verified INTEGER NOT NULL,
    user_confirmed INTEGER NOT NULL,
    external_action_performed INTEGER NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
