{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ ref('stg_github__events') }}

),

filtered AS (

    SELECT * FROM source
    WHERE event_type = 'PushEvent'

),

flattened AS (

    SELECT
        event_id,
        event_at,
        actor_id,
        actor_login,
        repo_id,
        repo_name,

        payload:push_id::number                     AS push_id,
        payload:ref::string                         AS ref,
        SPLIT_PART(payload:ref::string, '/', 3)     AS branch_name,
        payload:size::number                        AS commit_count,
        payload:distinct_size::number               AS distinct_commit_count,
        payload:head::string                        AS head_sha,
        payload:before::string                      AS before_sha

    FROM filtered

)

SELECT * FROM flattened
