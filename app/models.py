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
