CREATE TABLE IF NOT EXISTS configs (id BIGINT PRIMARY KEY,
                                    data JSON NOT NULL ,
                                    type TEXT NOT NULL);
