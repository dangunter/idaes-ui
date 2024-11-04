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
import enum
import importlib
from io import StringIO
from pathlib import Path
import pprint
import sys
from tempfile import TemporaryFile
from typing import TextIO
import warnings

try:
    import pyomo
    from pyomo.environ import Block, value
    from pyomo.network import Arc
    from pyomo.network.port import Port
except ImportError as err:
    pyomo = None
    warnings.warn(f"Could not import pyomo: {err}")    

AS_STRING = "-"


class OutputFormats(enum.Enum):
    markdown = "markdown"
    html = "html"
    mermaid = "mermaid"

    @classmethod
    def get_ext(cls, fmt):
        match fmt:
            case cls.html:
                result = "html"
            case cls.markdown:
                result = "md"
            case cls.mermaid:
                result = "mmd"
            case _:
                raise ValueError("Bad format")
        return result

class Mermaid:
    def __init__(self, connectivity, indent="   "):
        self._conn = connectivity
        self.indent = indent

    def write(self, output_file: str | None, output_format: str = None):
        if output_file is None:
            f = StringIO()
        else:
            f = open(output_file, "w")
        match output_format:
            case OutputFormats.markdown.value:
                f.write("# Graph\n```mermaid\n")
                self._body(f)
                f.write("\n```\n")
            case OutputFormats.mermaid.value:
                self._body(f)
            case OutputFormats.html.value:
                f.write("<!doctype html>\n<html lang='en'>\n<body>\n<pre class='mermaid'>\n")
                self._body(f)
                f.write("</pre>\n<script type='module'>\n")
                f.write("import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';\n")
                f.write("mermaid.initialize({securityLevel: 'loose', maxEdges: 2000});\n")
                f.write("await mermaid.run();\n")
                f.write("</script></body></html>")
            case _:
                raise ValueError(f"Bad output format: {output_format}")
        if output_file is None:
            return(f.getvalue())

    def _body(self, outfile):
        i = self.indent
        outfile.write("flowchart TD\n")
        # Get connections first, so we know which streams to show
        connections, show_streams = self._get_connections()
        # Units
        for s in self._get_mermaid_units():
            outfile.write(f"{i}{s}\n")
        # Streams
        for abbr, s in self._get_mermaid_streams():
            if abbr in show_streams:
                outfile.write(f"{i}{s}\n")
        # Connections
        for s in connections:
            outfile.write(f"{i}{s}\n")

    def _get_mermaid_units(self):
        for name, abbr in self._conn.units.items():
            yield f"{abbr}[{name}]"

    def _get_mermaid_streams(self):
        for name, abbr in self._conn.streams.items():
            yield abbr, f"{abbr}([{name}])"

    def _get_connections(self):
        connections = []
        show_streams = set()
        for stream_abbr, values in self._conn.connections.items():
            if values[0] is not None and values[1] is not None:
                connections.append(f"{values[0]} --> {values[1]}")
            elif values[0] is not None:
                connections.append(f"{values[0]} --> {stream_abbr}")
                show_streams.add(stream_abbr)
            elif values[1] is not None:
                connections.append(f" {stream_abbr} --> {values[1]}")
                show_streams.add(stream_abbr)
        return connections, show_streams


@dataclass
class Connectivity:
    units: dict = field(default_factory=dict)
    streams: dict = field(default_factory=dict)
    connections: dict = field(default_factory=dict)

class ConnectivityFile:
    """Build connectivity information from a file.
    """
    def __init__(self, input_file: str | Path | TextIO):
        if isinstance(input_file, str) or isinstance(input_file, Path):
            datafile = open(input_file, "r")
        else:
            datafile = input_file
        reader = csv.reader(datafile)
        self._header = next(reader)
        self._rows = list(reader)
        self._c = None

    @property
    def connectivity(self):
        if self._c is None:
            units = self._build_units()
            streams = self._build_streams()
            connections = self._build_connections(units, streams)
            self._c = Connectivity(units=units, streams=streams, connections=connections)
        return self._c

    def _build_units(self):
        units = {}
        c1, c2 = 1, -1
        for s in self._header[1:]:
            abbr = "Unit_"
            if c2 > -1:
                abbr += chr(ord("A") + c2)
            abbr += chr(ord("A") + c1)
            units[s] = abbr
            c1 += 1
            if c1 == 26:
                c1 = 0
                c2 += 1
        return units

    def _build_streams(self):
        streams = {}
        n = 3
        for row in self._rows[1:]:
            s = row[0]
            abbr = f"Stream_{n}"
            streams[s] = abbr
            n += 1
        return streams


    def _build_connections(self, units, streams):
        connections = {s: [None, None] for s in streams.values()}
        for row in self._rows[1:]:
            stream_name = row[0]
            col = 1
            for conn in row[1:]:
                if conn not in ("", "0"):
                    conn = max(0, int(conn))  # -1 -> 0, 1 -> 1
                    try:
                        unit_name = self._header[col]
                    except IndexError:
                        print(f"col={col} :: header-len={len(self._header)}")
                        raise
                    unit_abbr = units[unit_name]
                    stream_abbr = streams[stream_name]
                    connections[stream_abbr][conn] = unit_abbr
                col += 1
        return connections


class ModelConnectivity:
    """Build connectivity information from a model.
    """
    def __init__(self, model):
        if pyomo is None:
            raise NotImplementedError("Trying to build from a Pyomo model, but Pyomo is not installed")
        self._fs = model.fs
        self._units = []
        self._streams = []
        self._build()


    def _build(self):
        fs = self._fs  # alias
        units_ord, units_idx = {}, 0
        streams_ord, streams_idx = {}, 0
        rows, empty = [], True
        for comp in fs.component_objects(Arc, descend_into=False):
            stream_name = comp.getname()
            src, dst = comp.source.parent_block(), comp.dest.parent_block()
            src_name, dst_name = src.getname(), dst.getname()

            src_i, dst_i, stream_i = -1, -1, -1

            try:
                idx = streams_ord[stream_name]
            except KeyError:
                self._streams.append(stream_name)
                idx = streams_ord[stream_name] = streams_idx
                streams_idx += 1
                # if empty, there are no columns to lengthen; defer
                if empty:
                    rows = [[]]
                    empty = False
                else:
                    rows.append([0] * len(rows[0]))
            stream_i = idx
 
            for unit_name, is_src in (src_name, True), (dst_name, False):
                try:
                    idx = units_ord[unit_name]
                except KeyError:
                    self._units.append(unit_name)
                    idx = units_ord[unit_name] = units_idx
                    units_idx += 1
                    for row in rows:
                        row.append(0)
                if is_src:
                    src_i = idx
                else:
                    dst_i = idx

            rows[stream_i][src_i] = -1
            rows[stream_i][dst_i] = 1

        self._rows = rows
        

    def write(self, f: TextIO):
        header = self._units.copy()
        header.insert(0, "Units")
        f.write(",".join(header))
        f.write("\n")
        header_sep = ["" for _ in self._units]
        header_sep.insert(0, "Arcs")
        f.write(",".join(header_sep))
        f.write("\n")
        for row_idx, row in enumerate(self._rows):
            row.insert(0, self._streams[row_idx])
            f.write(",".join((str(value) for value in row)))
            f.write("\n")

    # def _identify_arcs(self):
    #     # Identify the arcs and known endpoints and store them
    #     for component in self.flowsheet.component_objects(Arc, descend_into=False):
    #         self.streams[component.getname()] = component
    #         self._known_endpoints.add(component.source.parent_block())
    #         self._known_endpoints.add(component.dest.parent_block())
    #         self._ordered_stream_names.append(component.getname())

    # def _identify_unit_models(self) -> dict:
    #     # pylint: disable=import-outside-toplevel
    #     from idaes.core import UnitModelBlockData  # avoid circular import
    #     from idaes.core.base.property_base import PhysicalParameterBlock, StateBlock

    #     # Create a map of components to their unit type
    #     components = {}

    #     # Identify the unit models and ports and store them
    #     for component in self.flowsheet.component_objects(Block, descend_into=True):
    #         if isinstance(component, UnitModelBlockData):
    #             # List of components is the same as the provided one
    #             components[component] = self.get_unit_model_type(component)
    #         elif isinstance(component, PhysicalParameterBlock) or isinstance(
    #             component, StateBlock
    #         ):
    #             # skip physical parameter / state blocks
    #             pass
    #         else:
    #             # Find unit models nested within indexed blocks
    #             type_ = self.get_unit_model_type(component)
    #             for item in component.parent_component().values():
    #                 if isinstance(item, UnitModelBlockData):
    #                     # See if this unit is connected to an arc
    #                     is_connected = False
    #                     for stream in self.streams.values():
    #                         if (
    #                             item == stream.source.parent_block()
    #                             or item == stream.dest.parent_block()
    #                         ):
    #                             is_connected = True
    #                             break
    #                     # Add to diagram if connected
    #                     if is_connected:
    #                         components[item] = type_

    #     return components


def get_model(module_name):
    mod = importlib.import_module(module_name)
    build_function = mod.build
    model = build_function()
    return model
    
def get_default_filename(fname: str, ext: str) -> str:
    i = fname.rfind(".")
    if i > 0:
        filename = fname[:i] + "." + ext
    else:
        filename = fname + + "." + ext
    return filename


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", help="Input CSV file", default=None)
    p.add_argument("-M", "--module", help="Input model's Python module", default=None)
    p.add_argument("--to", help="Packaging format for output mermaid graph",
                   choices=("markdown", "mermaid", "html"), default="mermaid")
    p.add_argument(
        "-O"
        "--output-file",
        dest="ofile",
        help=f"Output file (default=input with file extension changed, use '{AS_STRING}' to print)",
        default=None,
    )
    args = p.parse_args()

    # Sanity-check args
    if args.csv is None and args.module is None:
        p.error("Must specify one of --csv or -M/--module as input")
    elif all((args.csv, args.module)):
        p.error("Cannot specify more than one input method")

    # Initialize
    if args.csv is not None:
        conn_file = ConnectivityFile(args.csv)
    elif args.module is not None:
        try:
            model = get_model(args.module)
        except Exception as err:
            print("ERROR! Could not load model: {err}")
            sys.exit(1)
        model_conn = ModelConnectivity(model)
        with TemporaryFile(mode="w+t") as tempfile:
            model_conn.write(tempfile)
            tempfile.flush()  # make sure all data is written
            tempfile.seek(0)  # reset to start of file for reading
            conn_file = ConnectivityFile(tempfile)
    else:
        raise RuntimeError("No input method")

    # Build mermaid graph
    try:        
        mermaid = Mermaid(conn_file.connectivity)
    except Exception as err:
        print("ERROR! Could not parse connectivity information: {err}")
        print("Printing full stack trace below:")
        raise

    # Create output.
    if args.ofile == AS_STRING:
        print(mermaid.write(None, output_format=args.to))
    else:
        if args.ofile is None:
            ext = OutputFormats.get_ext(args.to)
            output_file = get_default_filename(args.ofile, ext)
        else:
            output_file = args.ofile
        mermaid.write(output_file, output_format=args.to)
