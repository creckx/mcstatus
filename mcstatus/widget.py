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

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))

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

    def __init__(self, *args, **kwargs):
        super(MinecraftWidgetCollector, self).__init__(*args, **kwargs)
        self.basic_status = self.get_status()
        self.full_info = self.get_rules()
        self.load_history()

    def save_history(self):
        with open(os.path.join(config["data_dir"], "minecraft_%s_%d.stats" % self.addr), "w") as f:
            json.dump(self.history, f)

    def save_data(self):
        with open(os.path.join(config["data_dir"], "minecraft_%s_%d.data" % self.addr), "w") as f:
            json.dump(self.get_data(), f)

    def load_history(self):
        if os.path.isfile(os.path.join(config["data_dir"], "minecraft_%s_%d.stats" % self.addr)):
            with open(os.path.join(config["data_dir"], "minecraft_%s_%d.stats" % self.addr)) as f:
                try:
                    self.history = json.load(f)
                    return 
                except ValueError:
                    pass
        self.history = {
            "players_24h": [],
            "last_hour": 0,
        }
        for x in range(24):
            self.history["players_24h"].append([])

    def get_last(self):
        with open(os.path.join(config["data_dir"], "minecraft_%s_%d.data" % self.addr)) as f:
            return json.load(f)

    def get_memory(self):
        output = {"memory": 0, "memory_max": 0}
        try:
            data = [x.strip().split() for x in run("ssh stats@%s free -m" % self.addr[0]).split("\n")]
            output["memory_max"] = data[1][1]
            output["memory"] = data[2][2]
        except IOError:
            pass
        return output

    def get_load(self):
        data = {"load": (0.0, 0.0, 0.0)}
        try:
            output = run("ssh stats@%s uptime" % self.addr[0]).strip()
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
            output = run("ssh stats@%s cat /proc/cpuinfo" % self.addr[0]).strip()
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
            self.history["players_24h"].append([players])
        else:
            self.history["players_24h"][-1].append(players)
        if len(self.history["players_24h"]) > 24:
            self.history["players_24h"] = self.history["players_24h"][1:]
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
        self.write_history(self.basic_status["numplayers"])
        return data

    def get_data(self):
        data = {}
        data.update(self.get_minecraft())
        data.update(self.get_cpus())
        data.update(self.get_load())
        data.update(self.get_memory())
        data["count_history"] = []
        for hour in self.history["players_24h"]:
            if len(hour) > 0:
                data["count_history"].append(sum(hour)/float(len(hour)))
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
    COLOR_GRAPH_LINE = (255, 178, 24)

    def __init__(self, data):
        self.data = data

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
                self.draw.line((x+1+i+offset, y+height-1, x+1+i+offset, y+height-1-(float(value)/ceil*height)), fill=self.COLOR_GRAPH_VALUE)
                offset += 1
        self.draw.text((x+2, y+height-14), unicode("0"), font=self.font, fill=self.COLOR_GRAPH_TEXT)
        self.draw.text((x+2, y+2), unicode(ceil), font=self.font, fill=self.COLOR_GRAPH_TEXT)
        self.draw.line((x+2, y+height, x+width+width*multiplicator, y+height), fill=self.COLOR_GRAPH_LINE)
        self.draw.line((x+2, y+2, x+width+width*multiplicator, y+2), fill=self.COLOR_GRAPH_LINE)
        self.draw.text(((x+(width+width*multiplicator)/2-8), y+height), unicode("24h"), font=self.font, fill=self.COLOR_GRAPH_TEXT)

    def draw_bar(self, x, y, percent, width=118):
        self.draw.rectangle((x, y, x+width, y+14), fill=self.COLOR_BAR_MAX)
        self.draw.rectangle((x+1, y+1, x+((width-1)/100.0)*percent, y+13), fill=self.COLOR_BAR_VALUE)

    def get_image(self):
        self.im = Image.new("RGB", (400, 120), self.COLOR_BG)
        self.draw = ImageDraw.Draw(self.im)
        self.font = ImageFont.truetype(os.path.join(ROOT, "DejaVuSans.ttf"), 12, encoding="unicode")

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


def main(hostname, port):
    collector = MinecraftWidgetCollector(hostname, port)
    collector.save_data()
    widget = MinecraftWidget(collector.get_last())
    with open(os.path.join(config["data_dir"], "www", "widget_%s_%d.png" % collector.addr), "w") as f:
        f.write(widget.get_image())


if __name__ == "__main__":
    main("194.8.253.48", 25565)
