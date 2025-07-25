-- migrate:up
CREATE TABLE pods (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    gpu_type TEXT NOT NULL,
    gpu_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    terminated_at TEXT,
    public_ip TEXT,
    cost_per_hr REAL
);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    pod_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT,
    error TEXT,
    FOREIGN KEY (pod_id) REFERENCES pods (id)
);

-- migrate:down
DROP TABLE jobs;
DROP TABLE pods;
