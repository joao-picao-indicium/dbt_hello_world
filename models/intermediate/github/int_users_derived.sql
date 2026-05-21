{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ ref('stg_github__events') }}

),

user_stats AS (

    SELECT
        actor_id,
        MIN(event_at) AS first_seen_at,
        MAX(event_at) AS last_seen_at,
        COUNT(*)       AS event_count
    FROM source
    GROUP BY actor_id

),

latest_user_attrs AS (

    SELECT
        actor_id,
        actor_login,
        actor_display_login
    FROM source
    QUALIFY ROW_NUMBER() OVER (PARTITION BY actor_id ORDER BY event_at DESC) = 1

),

final AS (

    SELECT
        latest_user_attrs.actor_id,
        latest_user_attrs.actor_login,
        latest_user_attrs.actor_display_login,
        user_stats.first_seen_at,
        user_stats.last_seen_at,
        user_stats.event_count
    FROM latest_user_attrs
    LEFT JOIN user_stats USING (actor_id)

)

SELECT * FROM final
