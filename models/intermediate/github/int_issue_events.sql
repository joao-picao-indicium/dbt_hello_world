{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ ref('stg_github__events') }}

),

filtered AS (

    SELECT * FROM source
    WHERE event_type = 'IssuesEvent'

),

flattened AS (

    SELECT
        event_id,
        event_at,
        actor_id,
        actor_login,
        repo_id,
        repo_name,

        payload:action::string                      AS action,

        payload:issue.id::number                    AS issue_id,
        payload:issue.number::number                AS issue_number,
        payload:issue.state::string                 AS issue_state,
        payload:issue.title::string                 AS issue_title,

        payload:issue.user.id::number               AS issue_author_id,
        payload:issue.user.login::string            AS issue_author_login,

        payload:issue.created_at::timestamp_ntz     AS issue_created_at,
        payload:issue.closed_at::timestamp_ntz      AS issue_closed_at,

        payload:issue.comments::number              AS comments_count

    FROM filtered

)

SELECT * FROM flattened
