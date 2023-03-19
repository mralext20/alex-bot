CREATE TABLE IF NOT EXISTS guilds(guildId BIGINT PRIMARY KEY,
                                 data STRING);


CREATE TABLE IF NOT EXISTS users(userId BIGINT PRIMARY KEY,
                                 data STRING);


CREATE TABLE IF NOT EXISTS rssFeedLastPosted(channelfeed STRING PRIMARY KEY,
                                 data STRING);

CREATE TABLE IF NOT EXISTS buttonRoles(data STRING);

CREATE TABLE IF NOT EXISTS movieSuggestions (data TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rssFeeds (data TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS recurringReminders (data TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS voiceNames (channelId BIGINT, userId BIGINT, name TEXT);