MYSQL_HOST="194.8.253.245"
MYSQL_PORT=3306
MYSQL_DB="besthostingcz_dd"
MYSQL_USERNAME="adam"
MYSQL_PASSWD=""

SQL_LIST = """
SELECT * 
FROM virtual_server AS vps, item AS i
WHERE 
i.id = vps.id 
AND
vps.vps_usage = 'minecraft'
AND 
(i.status = 'active' OR i.status = 'waiting')
AND 
vps.enabled = 1;
"""

SQL_PARMS = """
SELECT 
pa.id, pt.type, pt.description, pa.value
FROM 
virtual_server_param_abstract AS pa, virtual_server_param_type AS pt
WHERE 
pa.virtualServer_id = %d
AND 
pa.type_id = pt.id;
"""

SQL_IPS = """
SELECT ip.host, vps.name
FROM ip, item_ip, virtual_server vps
WHERE 
item_ip.item_id = %d
AND
vps.id = item_ip.item_id
AND
item_ip.ip_id = ip.id;
"""

SQL_PARM_UPDATE = """
UPDATE virtual_server_param_abstract a, virtual_server_param_type t
SET a.value = '%s'
WHERE a.type_id = t.id
AND a.virtualServer_id = %d
AND t.type = '%s';
"""

SQL_PARM_UPDATE_STR = """
UPDATE virtual_server_param_abstract a, virtual_server_param_type t
SET a.description = '%s'
WHERE a.type_id = t.id
AND a.virtualServer_id = %d
AND t.type = '%s'; 
"""

SQL_PARM_NAME = """
UPDATE virtual_server vps
SET vps.name = '%s'
WHERE vps.id = %d;
"""

SQL_GET_NAME = """
SELECT name FROM virtual_server WHERE id = %d;
"""
