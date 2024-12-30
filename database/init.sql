CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS steps (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) REFERENCES users(username) ON DELETE CASCADE,
    step_count INT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users(username, password) VALUES ('tester', 'password');
INSERT INTO steps(username, step_count, recorded_at) VALUES('tester', 999, CURRENT_TIMESTAMP);