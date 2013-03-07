#!/usr/bin/env python2
# coding: utf-8

import MySQLdb
import config
from widget import MinecraftWidget
from minecraft_query import MinecraftWidgetCollector


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
        self.players_online24 = {}

    def __str__(self):
        return "Minecraft IP: %s, DB_ID %d, CPU %s× (%s), RAM %s MB (%s MB)" % (self.ip, self.db_id, self.cpu, self.cpu_load, self.ram, float(self.ram_load))

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
        minecraft = MinecraftWidgetCollector("194.8.253.48", 25565)
        data = minecraft.get_data()
        #self.mc_version = data.get("")
        #self.mc_slots = data.get("count_max")
        #self.cpu_load = float(data["load"][1])/float(data["cpu_count"])*100
        #self.ram_load = float(data["memory"])/float(data["memory_max"])*100
        self.cpu_load = data["load"][1]
        self.ram_load = data["memory"]
        self.ram = data.get("memory_max")
        self.players_online = data.get("count")
        self.ping_status = data.get("delay")
        self._save_parms()

    def get_widget_data(self):
        return {
            "name": "Testovací server",
            "ip": self.ip,
            "port": 25565,
            "count": int(self.players_online),
            "memory": int(self.ram_load),
            "memory_max": int(self.ram),
            "load": float(self.cpu_load),
            "cpu_count": int(self.cpu),
            "count_history": self.players_online24,
        }

    def get_image(self):
        widget = MinecraftWidget(self.get_widget_data())
        return widget.get_image()



def main():
    servers = MinecraftServer.server_objects()
    for server in servers:
        print server
        #server.update_parms()
        with open("test.png", "w") as f:
            f.write(server.get_image())


if __name__ == "__main__":
    main()
