{{ config(materialized='view') }}

WITH source AS (

    SELECT * FROM {{ ref('stg_github__events') }}

),

filtered AS (

    SELECT * FROM source
    WHERE event_type = 'PullRequestEvent'

),

flattened AS (

    SELECT
        event_id,
        event_at,
        actor_id,
        actor_login,
        repo_id,
        repo_name,

        payload:action::string                          AS action,

        payload:pull_request.id::number                 AS pr_id,
        payload:pull_request.number::number             AS pr_number,
        payload:pull_request.state::string              AS pr_state,
        payload:pull_request.title::string              AS pr_title,

        payload:pull_request.user.id::number            AS pr_author_id,
        payload:pull_request.user.login::string         AS pr_author_login,

        payload:pull_request.merged::boolean            AS pr_merged,
        payload:pull_request.merged_at::timestamp_ntz   AS pr_merged_at,
        payload:pull_request.created_at::timestamp_ntz  AS pr_created_at,
        payload:pull_request.closed_at::timestamp_ntz   AS pr_closed_at,

        payload:pull_request.additions::number          AS additions,
        payload:pull_request.deletions::number          AS deletions,
        payload:pull_request.changed_files::number      AS changed_files,
        payload:pull_request.commits::number            AS commits_count

    FROM filtered

)

SELECT * FROM flattened
