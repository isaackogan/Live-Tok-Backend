# noinspection SqlNoDataSourceInspectionForFile

CREATE TABLE IF NOT EXISTS statistics
(

    streamer_id TEXT NOT NULL,
    viewer_id   TEXT NOT NULL,
    comments    INT  NOT NULL DEFAULT 0,
    experience  INT  NOT NULL DEFAULT 0,
    coins       INT NULL DEFAULT 0

);

