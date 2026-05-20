{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ source('github_archive', 'github_events') }}

),

deduped AS (

    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY raw_event:id::string
            ORDER BY ingested_at
        ) AS row_num
    FROM source

),

renamed AS (

    SELECT
        raw_event:id::string                    AS event_id,
        raw_event:type::string                  AS event_type,
        raw_event:created_at::timestamp_ntz     AS event_at,

        raw_event:actor.id::number              AS actor_id,
        raw_event:actor.login::string           AS actor_login,
        raw_event:actor.display_login::string   AS actor_display_login,

        raw_event:repo.id::number               AS repo_id,
        raw_event:repo.name::string             AS repo_name,

        raw_event:org.id::number                AS org_id,
        raw_event:org.login::string             AS org_login,

        raw_event:public::boolean               AS is_public,

        raw_event:payload                       AS payload,

        file_name,
        ingested_at

    FROM deduped
    WHERE row_num = 1
      AND raw_event:id IS NOT NULL

)

SELECT * FROM renamed
