import socket
import struct
import shlex
import ping
from subprocess import PIPE, Popen

class MinecraftQuery(object):
    MAGIC_PREFIX = '\xFE\xFD'
    PACKET_TYPE_CHALLENGE = 9
    PACKET_TYPE_QUERY = 0
    HUMAN_READABLE_NAMES = dict(
        game_id     = "Game Name",
        gametype    = "Game Type",
        motd        = "Message of the Day",
        hostname    = "Server Address",
        hostport    = "Server Port",
        map         = "Main World Name",
        maxplayers  = "Maximum Players",
        numplayers  = "Players Online",
        players     = "List of Players",
        plugins     = "List of Plugins",
        raw_plugins = "Raw Plugin Info",
        software    = "Server Software",
        version     = "Game Version",
    )
    
    def __init__(self, host, port, timeout=10, id=0, retries=2):
        self.addr = (host, port)
        self.id = id
        self.id_packed = struct.pack('>l', id)
        self.challenge_packed = struct.pack('>l', 0)
        self.retries = 0
        self.max_retries = retries
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
    
    def send_raw(self, data):
        self.socket.sendto(self.MAGIC_PREFIX + data, self.addr)
    
    def send_packet(self, type, data=''):
        self.send_raw(struct.pack('>B', type) + self.id_packed + self.challenge_packed + data)
    
    def read_packet(self):
        buff = self.socket.recvfrom(1460)[0]
        type = struct.unpack('>B', buff[0])[0]
        id = struct.unpack('>l', buff[1:5])[0]
        return type, id, buff[5:]
    
    def handshake(self, bypass_retries=False):
        self.send_packet(self.PACKET_TYPE_CHALLENGE)
        
        try:
            type, id, buff = self.read_packet()
        except:
            if not bypass_retries:
                self.retries += 1
            
            if self.retries < self.max_retries:
                self.handshake(bypass_retries=bypass_retries)
                return
            else:
                raise
        
        self.challenge = int(buff[:-1])
        self.challenge_packed = struct.pack('>l', self.challenge)
    
    def get_status(self):
        if not hasattr(self, 'challenge'):
            self.handshake()
        
        self.send_packet(self.PACKET_TYPE_QUERY)
        
        try:
            type, id, buff = self.read_packet()
        except:
            self.handshake()
            return self.get_status()
        
        data = {}
        
        data['motd'], data['gametype'], data['map'], data['numplayers'], data['maxplayers'], buff = buff.split('\x00', 5)
        data['hostport'] = struct.unpack('<h', buff[:2])[0]
        buff = buff[2:]
        data['hostname'] = buff[:-1]
        
        for key in ('numplayers', 'maxplayers'):
            try:
                data[key] = int(data[key])
            except:
                pass
        
        return data
    
    def get_rules(self):
        if not hasattr(self, 'challenge'):
            self.handshake()
        
        self.send_packet(self.PACKET_TYPE_QUERY, self.id_packed)
        
        try:
            type, id, buff = self.read_packet()
        except:
            self.retries += 1
            if self.retries < self.max_retries:
                self.handshake(bypass_retries=True)
                return self.get_rules()
            else:
                raise
        
        data = {}
        
        buff = buff[11:] # splitnum + 2 ints
        items, players = buff.split('\x00\x00\x01player_\x00\x00') # Shamefully stole from https://github.com/barneygale/MCQuery
        
        if items[:8] == 'hostname':
            items = 'motd' + items[8:]
        
        items = items.split('\x00')
        data = dict(zip(items[::2], items[1::2]))
        
        players = players[:-2]
        
        if players:
            data['players'] = players.split('\x00')
        else:
            data['players'] = []
        
        for key in ('numplayers', 'maxplayers', 'hostport'):
            try:
                data[key] = int(data[key])
            except:
                pass
        
        data['raw_plugins'] = data['plugins']
        data['software'], data['plugins'] = self.parse_plugins(data['raw_plugins'])
        
        return data
    
    def parse_plugins(self, raw):
        parts = raw.split(':', 1)
        server = parts[0].strip()
        plugins = []
        
        if len(parts) == 2:
            plugins = parts[1].split(';')
            plugins = map(lambda s: s.strip(), plugins)
        
        return server, plugins


def run(cmd):
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return stdout


class MinecraftWidgetCollector(MinecraftQuery):

    def __init__(self, *args, **kwargs):
        super(MinecraftWidgetCollector, self).__init__(*args, **kwargs)
        self.basic_status = self.get_status()
        self.full_info = self.get_rules()

    def get_delay(self):
        return {"delay": "1"}

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

    def get_minecraft(self):
        data = {
            "name": self.basic_status["motd"],
            "map" : self.basic_status["map"],
            "ip" : self.basic_status["hostname"],
            "port" : self.basic_status["hostport"],
            "version" : self.full_info["version"],
            "software" : self.full_info["software"],
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
        data.update(self.get_delay())
        return data