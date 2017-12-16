CREATE TABLE IF NOT EXISTS tags
               (hash TEXT PRIMARY KEY NOT NULL,
               tag TEXT NOT NULL,
               guild BIGINT NOT NULL,
               content TEXT NOT NULL,
               author BIGINT NOT NULL);

CREATE TABLE IF NOT EXISTS configs (id BIGINT PRIMARY KEY,
                                    data JSON NOT NULL ,
                                    type TEXT NOT NULL);


CREATE TABLE IF NOT EXISTS bank (owner BIGINT PRIMARY KEY,
                                 amount NUMERIC(15, 2) NOT NULL);


INSERT INTO tags (hash, tag, guild, content, author) VALUES
            ('1ca25c85001011127a3db6712b5e425b4ad4672c9754535b81e72f99c784112e',
            'hello world',
            295341979800436736,
            'hello, im ghost of b1nzy who wrote this tag',
            80351110224678912);

