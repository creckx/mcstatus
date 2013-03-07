#!/usr/bin/env python2

import MySQLdb
import config
import json

def get_mysql_conn():
    conn = MySQLdb.connect (
        host = config.MYSQL_HOST,
        port = config.MYSQL_PORT,
        user = config.MYSQL_USERNAME,
        passwd = config.MYSQL_PASSWD,
        db = config.MYSQL_DB
    )
    return conn


class MinecraftServer(object):

    def __init__(self):
        self.ip = None
        self.ipv6 = None
        self.db_id = None
        self.cpu = None
        self.ram = None
        self.hdd = None
        self.mc_version = None
        self.mc_slots = None
        self.cpu_load = None
        self.ram_load = None
        self.players_online = None
        self.whitelist = None
        self.ping_status = None
        self.players_online24 = []

    def __str__(self):
        return "Minecraft IP: %s, DB_ID %d, CPU %s (%s %%), RAM %s (%s %%)" % (self.ip, self.db_id, self.cpu, self.cpu_load, self.ram, self.ram_load)

    def __unicode__(self):
        return unicode(self.__str__())

    @staticmethod
    def server_objects():
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_LIST)
        servers = []
        for vps in cur.fetchall():
            server = MinecraftServer()
            server.db_id = vps[0]
            server._fetch_ips()
            server._fetch_parms()
            servers.append(server)
        return servers

    def _fetch_parms(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_PARMS % self.db_id)
        parms = ["cpu", "ram", "hdd", "mc_version", "mc_slots", "cpu_load", "ram_load", "players_online", "whitelist", "ping_status",]
        for parm in cur.fetchall():
            if parm[1] in parms:
                setattr(self, parm[1], parm[3])

    def _fetch_ips(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_IPS % self.db_id)
        for parm in cur.fetchall():
            if ":" in parm[0]:
                self.ipv6 = parm[0]
            else:
                self.ip = parm[0]
        
    def _save_parms(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_PARMS % self.db_id)
        parms = ["cpu_load", "ram_load", "players_online", "ping_status",]
        for parm in cur.fetchall():
            if parm[1] in parms:
                cur2 = conn.cursor()
                cur2.execute(config.SQL_PARM_UPDATE % (getattr(self, parm[1]), self.db_id, parm[1]))
        conn.commit()

    def update_parms(self):
        pass



def main():
    servers = MinecraftServer.server_objects()
    for server in servers:
        print server
        server.cpu_load = "12"
        server._save_parms()


if __name__ == "__main__":
    main()
