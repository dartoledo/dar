CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS runbooks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(3) -- Using a dummy 3-dimensional vector for now. Dify will re-embed this later with Gemini.
);

INSERT INTO runbooks (title, content, embedding)
VALUES (
    '500 Internal Server Error - Login Page',
    'SYMPTOM: The Go application login page is throwing a 500 Internal Server Error, and APM traces show a FATAL log regarding unexpected characters in password processing. CAUSE: There is a known bug where any password containing an exclamation point (!) will crash the system. ACTION: If you see this in the logs, immediately locate the user causing the traffic (e.g. admin:!admin), and temporarily suspend the account or patch the Go application to properly escape special characters in passwords.',
    '[0.1, 0.2, 0.3]'
);
