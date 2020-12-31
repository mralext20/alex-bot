CREATE TABLE IF NOT EXISTS configs (id BIGINT PRIMARY KEY,
                                    data JSON NOT NULL);


CREATE TABLE IF NOT EXISTS voiceData (id BIGINT PRIMARY KEY, 
                                      longestSession INTEGER, 
                                      lastStarted INTEGER, 
                                      averageDuration INTEGER DEFAULT 0,
                                      totalSessions INTEGER DEFAULT 0,
                                      currentlyRunning BOOLEAN);