{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ ref('stg_github__events') }}

),

repo_stats AS (

    SELECT
        repo_id,
        MIN(event_at) AS first_seen_at,
        MAX(event_at) AS last_seen_at,
        COUNT(*)       AS event_count
    FROM source
    GROUP BY repo_id

),

latest_repo_attrs AS (

    SELECT
        repo_id,
        repo_name,
        SPLIT_PART(repo_name, '/', 1) AS repo_owner,
        org_id,
        org_login
    FROM source
    QUALIFY ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY event_at DESC) = 1

),

final AS (

    SELECT
        latest_repo_attrs.repo_id,
        latest_repo_attrs.repo_name,
        latest_repo_attrs.repo_owner,
        latest_repo_attrs.org_id,
        latest_repo_attrs.org_login,
        repo_stats.first_seen_at,
        repo_stats.last_seen_at,
        repo_stats.event_count
    FROM latest_repo_attrs
    LEFT JOIN repo_stats USING (repo_id)

)

SELECT * FROM final
