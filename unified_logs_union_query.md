# Unified Logs UNION SQL Query

```sql
SELECT 
    datetime as timestamp,
    user_name,
    user_email,
    action,
    status,
    notes,
    log_source,
    company_name,
    partner_name,
    session_id,
    waypoint_id,
    waypoint_name,
    object_data,
    metadata
FROM (
    -- Portal Logs
    SELECT 
        CONCAT(pl.date, ' ', pl.time) as datetime,
        CONVERT(pl.name USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_name,
        CONVERT(pl.email USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_email,
        CONVERT(pl.action USING utf8mb4) COLLATE utf8mb4_unicode_ci as action,
        CONVERT(pl.status USING utf8mb4) COLLATE utf8mb4_unicode_ci as status,
        CONVERT(pl.notes USING utf8mb4) COLLATE utf8mb4_unicode_ci as notes,
        'portal_logs' COLLATE utf8mb4_unicode_ci as log_source,
        CONVERT(c.company_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as company_name,
        CONVERT(p.partner_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as partner_name,
        NULL as session_id,
        NULL as waypoint_id,
        NULL as waypoint_name,
        CONVERT(pl.object_data USING utf8mb4) COLLATE utf8mb4_unicode_ci as object_data,
        CONVERT(JSON_OBJECT('company_id', pl.company_id, 'partner_id', pl.partner_id, 'branch_id', pl.branch_id) USING utf8mb4) COLLATE utf8mb4_unicode_ci as metadata
    FROM fido1.portal_logs pl
    LEFT JOIN fido1.companies c ON pl.company_id = c.id
    LEFT JOIN fido1.partners p ON pl.partner_id = p.id
    WHERE 1=1

    UNION ALL

    -- App Logs
    SELECT 
        al.timestamp as datetime,
        CONVERT(CONCAT(u.first_name, ' ', u.last_name) USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_name,
        CONVERT(u.email USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_email,
        CONVERT(al.action USING utf8mb4) COLLATE utf8mb4_unicode_ci as action,
        CONVERT(al.status USING utf8mb4) COLLATE utf8mb4_unicode_ci as status,
        CONVERT(al.notes USING utf8mb4) COLLATE utf8mb4_unicode_ci as notes,
        'app_log' COLLATE utf8mb4_unicode_ci as log_source,
        CONVERT(c.company_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as company_name,
        CONVERT(p.partner_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as partner_name,
        al.session_id,
        al.waypoint_id,
        NULL as waypoint_name,
        NULL as object_data,
        CONVERT(JSON_OBJECT('user_id', al.user_id, 'dma_id', al.dma_id) USING utf8mb4) COLLATE utf8mb4_unicode_ci as metadata
    FROM fido1.app_log al
    LEFT JOIN fido1.users_portal u ON al.user_id = u.id
    LEFT JOIN fido1.companies c ON u.company_id = c.id
    LEFT JOIN fido1.partners p ON u.partner_id = p.id
    WHERE 1=1

    UNION ALL

    -- Waypoint Logs
    SELECT 
        wl.datetime,
        CONVERT(CONCAT(u.first_name, ' ', u.last_name) USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_name,
        CONVERT(u.email USING utf8mb4) COLLATE utf8mb4_unicode_ci as user_email,
        CONVERT(CONCAT('Status Change: ', wl.status_changed_from_id, '→', wl.status_changed_to_id) USING utf8mb4) COLLATE utf8mb4_unicode_ci as action,
        'completed' COLLATE utf8mb4_unicode_ci as status,
        CONVERT(wl.notes USING utf8mb4) COLLATE utf8mb4_unicode_ci as notes,
        'waypoint_logs' COLLATE utf8mb4_unicode_ci as log_source,
        CONVERT(c.company_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as company_name,
        CONVERT(p.partner_name USING utf8mb4) COLLATE utf8mb4_unicode_ci as partner_name,
        NULL as session_id,
        wl.waypoint_id,
        NULL as waypoint_name,
        NULL as object_data,
        CONVERT(JSON_OBJECT('user_id', wl.user_id) USING utf8mb4) COLLATE utf8mb4_unicode_ci as metadata
    FROM fido_way.waypoint_logs wl
    LEFT JOIN fido1.users_portal u ON wl.user_id = u.id
    LEFT JOIN fido1.companies c ON u.company_id = c.id
    LEFT JOIN fido1.partners p ON u.partner_id = p.id
    WHERE 1=1
) unified_logs
WHERE 1=1
ORDER BY datetime DESC
LIMIT 100;
``` 