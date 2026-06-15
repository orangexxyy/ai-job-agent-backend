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
