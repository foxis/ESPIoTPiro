""" A simple MQTT Client application to gather Weather Station data.

This application subscribes to topics for each station and gathers data into
a dictionary of dictionaries. Saves the data into a CSV file.
Optionally displays the data.

"""

import paho.mqtt.client as mqtt
import argparse
from datetime import datetime
import os
import threading as thrd

try:
    import matplotlib.pyplot as plt
    matplotlib_available = True
except :
    matplotlib_available = False

class UserData(object):
    def __init__(self, filename, topics, verbose, plot, max_plot):
        self.filename = filename
        self.topics = topics
        self.verbose = verbose
        self.plot = plot
        self.lock = thrd.Lock()
        self.readings = {topic: [] for topic in topics}
        self.plots = None
        self.max_plot = max_plot
        self.default_plot = {topic: [[], []] for topic in topics}
        self._connected = False
        self._last_connected = False

        if os.path.exists(filename) and plot:
            with open(filename) as f:
                header = []
                for i, line in enumerate(f.readlines()):
                    data = line.split(',')
                    if i == 0:
                        header = data
                    else:
                        for topic, val in zip(header[1:], data[1:]):
                            if topic in topics:
                                self.default_plot[topic][0] += [data[0]]
                                self.default_plot[topic][1] += [float(val)]
                                self.default_plot[topic][0] = self.default_plot[topic][0][-self.max_plot:]
                                self.default_plot[topic][1] = self.default_plot[topic][1][-self.max_plot:]

    @property
    def connected(self):
        with self.lock:
            return self._connected

    @connected.setter
    def connected(self, value):
        with self.lock:
            self._connected = value

    @property
    def last_connected(self):
        with self.lock:
            return self._last_connected

    @last_connected.setter
    def connected(self, value):
        with self.lock:
            self._last_connected = value

    def add_reading(self, topic, data):
        with self.lock:
            readings = self.readings
            if topic not in readings:
                return
            readings[topic] += [data]

            if self.verbose:
                print(topic, data)

            if self.plot:
                self.plot_reading(topic, data)

            self.write_last_reading(topic)

    def write_last_reading(self, topic):
        readings = self.readings
        line = "{},{},{}".format(datetime.now(), topic, readings[topic][-1])
        write_headers = not os.path.exists(self.filename)
        with open(self.filename, "a") as f:
            if write_headers:
                header = "date,topic,data"
                print(header)
                f.writelines([header, "\n"])
            print(line)
            f.writelines([line, "\n"])

    def create_plots(self, topics):
        plots = dict(fig=plt.figure())
        N = len(topics)
        plots.update({
            topic: {
                'x': self.default_plot[topic][0],
                'y': self.default_plot[topic][1],
                'plot': plots['fig'].add_subplot(N, 1, i + 1)
            } for i, topic in enumerate(topics)
        })
        plots['fig'].suptitle(topic)
        return plots

    def plot_reading(self, topic, data):
        if data == 'nan':
            return

        if not self.plots:
            self.plots = {station: self.create_plots(station, self.topics) for station in self.stations}

        self.plots[station][topic]['x'] += ["{}t".format(datetime.now())]
        self.plots[station][topic]['y'] += [float(data)]

        self.plots[station][topic]['x'] = self.plots[station][topic]['x'][-self.max_plot:]
        self.plots[station][topic]['y'] = self.plots[station][topic]['y'][-self.max_plot:]

        self.plots[station][topic]['plot'].clear()
        self.plots[station][topic]['plot'].plot(
            self.plots[station][topic]['x'],
            self.plots[station][topic]['y'])


def on_disconnect(client, userdata, rc):
    print("Disconnected %i" % rc)
    userdata.connected = False


def on_connect(client, userdata, flags, rc):
    print("Connected %i" % rc)
    if rc == 0:
        for topic in userdata.topics:
            client.subscribe(topic)
        userdata.connected = True
        userdata.last_connected = True


def on_message(client, userdata, message):
    data = str(message.payload.decode("utf-8"))
    try:
        userdata.add_reading(message.topic, data)
    except Exception as e:
        print("Exception occured: %s" % repr(e))


def main(name, username, password, url, port, topics, filename, verbose, plot, max_plot):

    userdata = UserData(filename, topics, verbose, plot, max_plot)

    client = mqtt.Client(name, userdata=userdata)
    client.username_pw_set(username, password)
    client.connect(url, port)

    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if not plot:
        client.loop_start()
        raw_input("Press Enter or Ctrl+C to stop")
        client.loop_stop()
    else:
        while True:
            client.loop()
            plt.draw()
            plt.pause(0.01)
            if not userdata.connected and userdata.last_connected:
                userdata.last_connected = False
                client.connect(url, port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Client for Weather Station readings monitoring.")
    parser.add_argument("server",
                        help="MQTT Server Address")
    parser.add_argument("name",
                        help="MQTT Client Name (default P1)")
    parser.add_argument("-u", "--username",
                        help="MQTT Client Username")
    parser.add_argument("-l", "--password",
                        help="MQTT Client Password")
    parser.add_argument("-p", "--port", type=int, default=16769,
                        help="MQTT Server Port")
    parser.add_argument("-t", "--topics", required=True,
                        help="Comma separated list of topics to monitor")
    parser.add_argument("-f", "--file", default=None,
                        help="CSV file to write readings to (default {client name}.csv)")
    parser.add_argument("-v", "--verbose", const=True, default=False, action='store_const',
                        help="Verbose output to stdout")
    parser.add_argument("-P", "--plot", const=matplotlib_available, default=False, action='store_const',
                        help="Plot graphs of the readings (matplotlib importable=%s)" % str(matplotlib_available))
    parser.add_argument("-n", "--max_plot", default=120,
                        help="Maximum number of points to plot (default 120)")
    args = parser.parse_args()

    filename = args.file if args.file else "{}.csv".format(args.name)

    main(args.name, args.username, args.password,
         args.server, args.port,
         args.topics.split(','), filename, args.verbose,
         args.plot, args.max_plot)
