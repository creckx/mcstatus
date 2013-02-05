# coding: utf-8

import StringIO
import shlex
import os
import sys
import json
import datetime
from minecraft_query import MinecraftQuery
from PIL import Image, ImageDraw, ImageFont
from subprocess import PIPE, Popen

#Doc
#http://www.pythonware.com/library/pil/handbook/imagedraw.htm
#http://stackoverflow.com/questions/4011705/python-the-imagingft-c-module-is-not-installed (_imaging)

"""
map = world
motd = BEST-HOSTING s.r.o.
hostname = 194.8.253.48
numplayers = 6
gametype = SMP
maxplayers = 40
hostport = 25565

map = world
motd = BEST-HOSTING s.r.o.
hostport = 25565
numplayers = 6
gametype = SMP
players = ['janice158', 'nitramek2013', 'batman', 'Fox24', 'adelka', 'HunySss']
version = 1.4.5
maxplayers = 40
plugins = ['WorldEdit 5.4.2', 'iConomy 7.0', 'HawkEye 1.1.0', 'Vault 1.2.13-b148', 'PermissionsEx 1.19.1', 'LWC 4.3.1 (b767-git-MANUAL) (November 15, 2012)', 'WorldGuard 644-6df9c36', 'Essentials 2.9.3', 'dynmap 0.70.3-1298', 'Dynmap-WorldGuard 0.30', 'EssentialsProtect 2.9.3', 'AuthMe 2.6.7b5', 'Dynmap-Essentials 0.30', 'EssentialsSpawn 2.9.3', 'DragonTravel 1.7.1', 'ChestShop 3.46', 'EssentialsChat 2.9.3']
raw_plugins = CraftBukkit on Bukkit 1.4.5-R0.2: WorldEdit 5.4.2; iConomy 7.0; HawkEye 1.1.0; Vault 1.2.13-b148; PermissionsEx 1.19.1; LWC 4.3.1 (b767-git-MANUAL) (November 15, 2012); WorldGuard 644-6df9c36; Essentials 2.9.3; dynmap 0.70.3-1298; Dynmap-WorldGuard 0.30; EssentialsProtect 2.9.3; AuthMe 2.6.7b5; Dynmap-Essentials 0.30; EssentialsSpawn 2.9.3; DragonTravel 1.7.1; ChestShop 3.46; EssentialsChat 2.9.3
game_id = MINECRAFT
hostip = 194.8.253.48
software = CraftBukkit on Bukkit 1.4.5-R0.2

"""

config = {
    "data_dir": "/var/lib/minecraft/",
}

if not os.path.isdir(config["data_dir"]):
    try:
        os.makedirs(config["data_dir"])
        os.makedirs(os.path.join(config["data_dir"], "www"))
    except OSError:
        sys.stderr.write("ERROR: i don't have permissions for %s\n" % config["data_dir"])
        sys.exit(1)


def run(cmd):
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return stdout

class MinecraftWidgetCollector(MinecraftQuery):

    def __init__(self, ssh_connection, *args, **kwargs):
        super(MinecraftWidgetCollector, self).__init__(*args, **kwargs)
        self.basic_status = self.get_status()
        self.full_info = self.get_rules()
        self.ssh_connection = ssh_connection
        self.load_history()

    def save_history(self):
        with open(os.path.join(config["data_dir"], "minecraft.stats"), "w") as f:
            json.dump(self.history, f)

    def save_data(self):
        with open(os.path.join(config["data_dir"], "minecraft.data"), "w") as f:
            json.dump(self.get_data(), f)

    def load_history(self):
        if os.path.isfile(os.path.join(config["data_dir"], "minecraft.stats")):
            with open(os.path.join(config["data_dir"], "minecraft.stats")) as f:
                try:
                    self.history = json.load(f)
                    return 
                except ValueError:
                    pass
        self.history = {
            "players_24h": {},
            "last_hour": 0,
        }
        for x in range(24):
            self.history["players_24h"][x] = []

    def get_memory(self):
        output = {"memory": 0, "memory_max": 0}
        try:
            data = [x.strip().split() for x in run("ssh %s free -m" % self.ssh_connection).split("\n")]
            output["memory_max"] = data[1][1]
            output["memory"] = data[2][2]
        except IOError:
            pass
        return output

    def get_load(self):
        data = {"load": (0.0, 0.0, 0.0)}
        try:
            output = run("ssh %s uptime" % self.ssh_connection).strip()
        except IOError:
            pass
        if len(output.split(" ")) > 3:
            load1m = float(output.split(" ")[-1].strip(" ,").replace(",", "."))
            load5m = float(output.split(" ")[-2].strip(" ,").replace(",", "."))
            load15m = float(output.split(" ")[-3].strip(" ,").replace(",", "."))
            data["load"] = (load1m, load5m, load15m)
        return data

    def get_cpus(self):
        data = {"cpu_count": 1}
        try:
            output = run("ssh %s cat /proc/cpuinfo" % self.ssh_connection).strip()
        except IOError:
            output = ""
        if output:
            cpus = []
            for x in [x.strip() for x in output.split("\n")]:
                if "processor" in x:
                    cpus.append(int(x.split()[2].strip()))
            data["cpu_count"] = max(cpus)+1 if cpus else 1
        return data

    def write_history(self, players):
        hour = datetime.datetime.now().hour
        if hour != self.history["last_hour"]:
            self.history["players_24h"][hour] = [players]
        else:
            self.history["players_24h"][hour].append(players)
        self.history["last_hour"] = hour
        self.save_history()

    def get_minecraft(self):
        data = {
            "name": self.basic_status["motd"],
            "map" : self.basic_status["map"],
            "ip" : self.basic_status["hostname"],
            "port" : self.basic_status["hostport"],
            "count" : self.basic_status["numplayers"],
            "count_max" : self.basic_status["maxplayers"],
        }
        return data

    def get_data(self):
        data = {}
        data.update(self.get_minecraft())
        data.update(self.get_cpus())
        data.update(self.get_load())
        data.update(self.get_memory())
        data["count_history"] = []
        for h in self.history["players_24h"]:
            if len(self.history["players_24h"][h]) > 0:
                data["count_history"].append(sum(self.history["players_24h"][h])/len(self.history["players_24h"][h]))
            else:
                data["count_history"].append(0)
        return data


class MinecraftWidget(object):
    COLOR_BG = (106, 137, 94)
    COLOR_TEXT = (137, 41, 0)
    COLOR_TEXT_VALUE = (211, 211, 211)
    COLOR_BAR_MAX = (20, 20, 20)
    COLOR_BAR_VALUE = (80, 250, 34)
    COLOR_GRAPH_MAX = (20, 20, 20)
    COLOR_GRAPH_VALUE = (250, 20, 34)
    COLOR_GRAPH_TEXT = (250, 250, 250)

    def __init__(self, data={}):
        self.im = Image.new("RGB", (400, 120), self.COLOR_BG)

        self.draw = ImageDraw.Draw(self.im)
        self.font = ImageFont.truetype("DejaVuSans.ttf", 12, encoding="unicode")
        if data:
            self.data = data
        else:
            self.data = self.load_data()

    def load_data(self):
        with open(os.path.join(config["data_dir"], "minecraft.data")) as f:
            return json.load(f)

    def draw_name(self, x ,y):
        self.draw.text((x, y), unicode("Server"), font=self.font, fill=self.COLOR_TEXT)
        self.draw.text((x+52, y), unicode(self.data["name"]), font=self.font, fill=self.COLOR_TEXT_VALUE)

    def draw_ip(self, x ,y):
        #self.draw.text((x, y), unicode("IP"), font=self.font, fill=self.COLOR_TEXT)
        self.draw.text((x+20, y), unicode(self.data["ip"]), font=self.font, fill=self.COLOR_TEXT_VALUE)

    def draw_count(self, x ,y):
        self.draw.text((x, y), unicode("Hráči"), font=self.font, fill=self.COLOR_TEXT)
        self.draw.text((x+42, y), unicode(self.data["count"]), font=self.font, fill=self.COLOR_TEXT_VALUE)

    def draw_load(self, x ,y, load):
        self.draw.text((x, y), unicode("Zatížení"), font=self.font, fill=self.COLOR_TEXT)
        self.draw.text((x+60, y), unicode("%.2f %%" % load), font=self.font, fill=self.COLOR_TEXT_VALUE)

    def draw_memory(self, x ,y):
        self.draw.text((x, y), unicode("Paměť"), font=self.font, fill=self.COLOR_TEXT)
        self.draw.text((x+45, y), unicode("%s/%s MB" % (self.data["memory"], self.data["memory_max"])), font=self.font, fill=self.COLOR_TEXT_VALUE)

    def draw_graphs(self, x, y, values, height=40, multiplicator=1):
        width=len(values)
        ceil = max(values)*1.2
        if not ceil: ceil = 1
        self.draw.rectangle((x, y, x+width*(multiplicator+1)+2, y+height+2), fill=self.COLOR_GRAPH_MAX)
        offset = 1
        for i, value in enumerate(values):
            for offset_local in range(multiplicator):
                self.draw.line((x+1+i+offset, y+height-1, x+1+i+offset, y+height-1-(value/ceil*height)), fill=self.COLOR_GRAPH_VALUE)
                offset += 1
        self.draw.text((x+2, y+height-12), unicode("0"), font=self.font, fill=self.COLOR_GRAPH_TEXT)
        self.draw.text((x+2, y+2), unicode(ceil), font=self.font, fill=self.COLOR_GRAPH_TEXT)

    def draw_bar(self, x, y, percent, width=118):
        self.draw.rectangle((x, y, x+width, y+14), fill=self.COLOR_BAR_MAX)
        self.draw.rectangle((x+1, y+1, x+((width-1)/100.0)*percent, y+13), fill=self.COLOR_BAR_VALUE)

    def get_image(self):
        self.draw_name(10, 10)
        self.draw_ip(230, 10)
        self.draw_count(230, 30)
        load = float(self.data["load"][1])/float(self.data["cpu_count"])*100
        self.draw_load(10, 30, load)
        self.draw_memory(10, 70)
        self.draw_bar(10, 50, int(load), 200)
        self.draw_bar(10, 90, float(self.data["memory"])/float(self.data["memory_max"])*100, 200)
        self.draw_graphs(230, 50, self.data["count_history"], 52, 4)

        output = StringIO.StringIO()
        self.im.save(output, "PNG")
        return output.getvalue()


def main(hostname, port, ssh_connection):
    collector = MinecraftWidgetCollector(ssh_connection, hostname, port)
    collector.save_data()
    widget = MinecraftWidget()
    with open(os.path.join(config["data_dir"], "www", "widget.png"), "w") as f:
        f.write(widget.get_image())


if __name__ == "__main__":
    main("194.8.253.48", 25565, "bestnet-minecraft")
