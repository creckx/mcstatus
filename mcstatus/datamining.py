#!/usr/bin/env python2
# coding: utf-8

import MySQLdb
import config
import datetime
import json
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
        self.name = None
        self.cpu = None
        self.ram = None
        self.hdd = None
        self.mc_map = None
        self.mc_version = None
        self.mc_slots = None
        self.cpu_load = None
        self.ram_load = None
        self.players_online = None
        self.whitelist = None
        self.ping_status = 0
        self.players_online_24 = None

    def __str__(self):
        return "Minecraft server %s IP: %s, DB_ID %d, CPU %s× (%s), RAM %s MB (%s MB)" % (self.name, self.ip, self.db_id, self.cpu, self.cpu_load, self.ram, float(self.ram_load))

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

    @staticmethod
    def server_object(vid):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_LIST)
        for vps in cur.fetchall():
            if int(vps[0]) == int(vid):
                server = MinecraftServer()
                server.db_id = vps[0]
                server._fetch_ips()
                server._fetch_parms()
                return server
        return None

    def _fetch_parms(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_PARMS % self.db_id)
        parms = ["cpu", "ram", "hdd", "mc_map", "mc_version", "mc_slots", "cpu_load", "ram_load", "players_online", "whitelist", "ping_status", "players_online_24"]
        for parm in cur.fetchall():
            if parm[1] in parms:
                setattr(self, parm[1], parm[3])
        if self.players_online_24:
            self.players_online_24 = json.loads(self.players_online_24)
        if self.cpu_load:
            self.cpu_load = float(self.cpu_load) / 100
        self._fetch_name()

    def _fetch_ips(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_IPS % self.db_id)
        for parm in cur.fetchall():
            if ":" in parm[0]:
                self.ipv6 = parm[0]
            else:
                self.ip = parm[0]

    def _fetch_name(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(config.SQL_GET_NAME % self.db_id)
        self.name = cur.fetchone()[0]
        
    def _save_parms(self):
        conn = get_mysql_conn()
        cur = conn.cursor()
        parm = "cpu_load"
        cur.execute(config.SQL_PARM_UPDATE % (int(getattr(self, parm)*100), self.db_id, parm))
        parm = "ram_load"
        cur.execute(config.SQL_PARM_UPDATE % (getattr(self, parm), self.db_id, parm))
        parm = "players_online"
        cur.execute(config.SQL_PARM_UPDATE % (getattr(self, parm), self.db_id, parm))
        parm = "ping_status"
        cur.execute(config.SQL_PARM_UPDATE % (getattr(self, parm), self.db_id, parm))
        parm = "mc_map"
        cur.execute(config.SQL_PARM_UPDATE_STR % (getattr(self, parm), self.db_id, parm))
        parm = "players_online_24"
        cur.execute(config.SQL_PARM_UPDATE_STR % (json.dumps(getattr(self, parm)), self.db_id, parm))
        cur.execute(config.SQL_PARM_NAME % (getattr(self, "name"), self.db_id))
        conn.commit()

    def process_history(self, players_online):
        hour = datetime.datetime.now().hour
        if not self.players_online_24:
            self.players_online_24 = {"last_hour": 0, "history": {}}
        if self.players_online_24.get("last_hour", 0) != hour:
            self.players_online_24[hour] = []
            self.players_online_24["last_hour"] = hour
        if not hour in self.players_online_24["history"]:
            self.players_online_24["history"][hour] = [players_online]
        else:
            self.players_online_24["history"][hour].append(players_online)

    def update_parms(self):
        minecraft = MinecraftWidgetCollector("194.8.253.48", 25565)
        data = minecraft.get_data()
        #self.mc_version = data.get("")
        #self.cpu_load = float(data["load"][1])/float(data["cpu_count"])*100
        #self.ram_load = float(data["memory"])/float(data["memory_max"])*100
        self.name = data.get("name")
        self.mc_real_slots = data.get("count_max")
        self.mc_map = data["map"]
        self.cpu_load = data["load"][1]
        self.ram_load = data["memory"]
        self.ram = data.get("memory_max")
        self.players_online = data["count"]
        self.ping_status = 1
        self.process_history(data["count"])
        self._save_parms()

    def get_widget_data(self):
        return {
            "name": self.name,
            "ip": self.ip,
            "port": 25565,
            "count": int(self.players_online),
            "memory": int(self.ram_load),
            "memory_max": int(self.ram),
            "load": float(self.cpu_load),
            "cpu_count": int(self.cpu),
            "history": self.players_online_24.get("history", []) if self.players_online_24 else [],
        }

    def get_image(self):
        widget = MinecraftWidget(self.get_widget_data())
        return widget.get_image()



def main():
    servers = MinecraftServer.server_objects()
    for server in servers:
        server.update_parms()
        print server, "... fetched"
        #with open("test.png", "w") as f:
        #    f.write(server.get_image())


if __name__ == "__main__":
    main()
