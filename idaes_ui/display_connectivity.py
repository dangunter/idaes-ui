"""
Display a graph derived from a connectivity matrix from a comma-separated values file

Input format::

    Units,Unit 1 name,Unit 2 Name, ..., Unit N Name
    Arcs,,,,,,,	...,
    Arc1 Name,	-1,	0, 0, ..., 0
    Arc2 Name, 0 , 1, 0 ,... , 0

Where each cell at the intersection of an Arc (row i) and Unit (column j)
is either:
  *  -1 meaning Arc(i) is an outlet of Unit(j), 
  *  1 meaning Arc(i) is an inlet for Unit(j),
  *  0 meaning there is no connection

The output will be a minimal HTML page that uses the Mermaid JavaScript library
to render a graph of the connectivity.

If the "--md" option is given the output will instead be a Markdown file
that has embedded Mermaid, which can be rendered natively by GitHub.

Run this script with the "-h/--help" option for help on usage.
"""

import argparse
import csv
from dataclasses import dataclass, field
from io import StringIO


@dataclass
class MermaidData:
    units: list = field(default_factory=list)
    stream: dict = field(default_factory=dict)
    connections: list = field(default_factory=list)
    show_streams: list = field(default_factory=list)
    indent: str = "    "

    def as_html(self, outfile):
        outfile.write(
            """<!doctype html>
        <html lang="en">
        <body>
            <pre class="mermaid">\n"""
        )
        self._body(outfile)
        outfile.write(
            """
            </pre>
            <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
            mermaid.initialize({securityLevel: 'loose', maxEdges: 2000});
            await mermaid.run();
            </script>
        </body>
        </html>"""
        )

    def as_markdown(self, outfile):
        outfile.write("# Graph\n```mermaid\n")
        self._body(outfile)
        outfile.write("\n```\n")

    def as_mermaid(self, outfile):
        self._body(outfile)

    def _body(self, outfile):
        i = self.indent
        outfile.write("flowchart TD\n")
        # Units
        for s in self.units:
            outfile.write(f"{i}{s}\n")
        # Streams
        for abbr, s in self.streams.items():
            if abbr in self.show_streams:
                outfile.write(f"{i}{s}\n")
        # Connections
        for s in self.connections:
            outfile.write(f"{i}{s}\n")


class Connectivity:
    def __init__(self, input_file):
        datafile = open(input_file, "r")
        self._input_file = input_file
        reader = csv.reader(datafile)
        self._header = next(reader)
        self._rows = list(reader)
        self.mermaid = MermaidData()
        self._build()

    @staticmethod
    def _change_ext(fname, ext):
        i = fname.rfind(".")
        if i > 0:
            filename = fname[:i] + ext
        else:
            filename = fname + ext
        return filename

    @staticmethod
    def _as_string(fn) -> str:
        sio = StringIO()
        fn(sio)
        return sio.getvalue()

    def as_html(self, filename=None) -> None:
        if filename is None:
            filename = self._change_ext(self._input_file, ".html")
        with open(filename, "w") as outfile:
            self.mermaid.as_html(outfile)

    def as_html_string(self) -> str:
        return self._as_string(self.mermaid.as_html)

    def as_markdown(self, filename=None) -> None:
        if filename is None:
            filename = self._change_ext(self._input_file, ".md")
        with open(filename, "w") as outfile:
            self.mermaid.as_markdown(outfile)

    def as_markdown_string(self) -> str:
        return self._as_string(self.mermaid.as_markdown)

    def as_mermaid(self, filename=None) -> None:
        if filename is None:
            filename = self._change_ext(self._input_file, ".mmd")
        with open(filename, "w") as outfile:
            self.mermaid.as_mermaid(outfile)

    def as_mermaid_string(self) -> str:
        return self._as_string(self.mermaid.as_mermaid)

    def _build(self):
        self.units, self.mermaid.units = self._build_units()
        self.streams, self.mermaid.streams = self._build_streams()
        self.mermaid.connections, self.mermaid.show_streams = self._build_connections(
            self._build_connection_data()
        )

    def _build_units(self):
        units = {}
        mermaid_units = []
        c1, c2 = 1, -1
        for s in self._header[1:]:
            abbr = "Unit_"
            if c2 > -1:
                abbr += chr(ord("A") + c2)
            abbr += chr(ord("A") + c1)
            mermaid_unit = f"{abbr}[{s}]"
            units[s] = abbr
            mermaid_units.append(mermaid_unit)
            c1 += 1
            if c1 == 26:
                c1 = 0
                c2 += 1
        return units, mermaid_units

    def _build_streams(self):
        streams = {}
        mermaid_streams = {}
        n = 3
        for row in self._rows[1:]:
            s = row[0]
            abbr = f"Stream_{n}"
            mermaid_stream = f"{abbr}([{s}])"
            streams[s] = abbr
            mermaid_streams[abbr] = mermaid_stream
            n += 1
        return streams, mermaid_streams

    def _build_connection_data(self):
        connection_data = {s: [None, None] for s in self.streams.values()}
        for row in self._rows[1:]:
            stream_name = row[0]
            col = 1
            for conn in row[1:]:
                if conn not in ("", "0"):
                    conn = max(0, int(conn))  # -1 -> 0, 1 -> 1
                    unit_name = self._header[col]
                    unit_abbr = self.units[unit_name]
                    stream_abbr = self.streams[stream_name]
                    # print(f"{stream_name} {stream_abbr} : {conn}")
                    connection_data[stream_abbr][conn] = unit_abbr
                col += 1
        return connection_data

    def _build_connections(self, connection_data):
        connections = []
        show_streams = set()
        for stream_abbr, values in connection_data.items():
            if values[0] is not None and values[1] is not None:
                connections.append(f"{values[0]} --> {values[1]}")
            elif values[0] is not None:
                connections.append(f"{values[0]} --> {stream_abbr}")
                show_streams.add(stream_abbr)
            elif values[1] is not None:
                connections.append(f" {stream_abbr} --> {values[1]}")
                show_streams.add(stream_abbr)
        return connections, show_streams


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("filename", help="Input filename (CSV file)")
    p.add_argument("-f", "--format", help="Format",
                   choices=("markdown", "mermaid", "html"), default="html")
    p.add_argument(
        "--ofile",
        help="Output file (default=input with file extension changed)",
        default=None,
    )
    args = p.parse_args()

    try:
        conn = Connectivity(args.filename)
    except Exception as err:
        print("ERROR! Could not parse connectivity information: {err}")
        print("Printing full stack trace below:")
        raise

    # call method name matching desired output format
    method_name = f"as_{args.format}"
    if args.ofile == "-":
        print(getattr(conn, method_name + "_string")())
    else:
        getattr(conn, method_name)(filename=args.ofile)
