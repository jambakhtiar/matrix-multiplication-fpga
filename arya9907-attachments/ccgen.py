import numpy as np

from hwgen import *
from computationcoding.csd_conv import to_csd


def get_shifts(n, w, d):
    """Helper function to generate minimal set of required shifts for
    multiplication of a given fixed point.

    :n: input float number
    :w: total bit width
    :d: number of decimal bits
    :returns: list of shifts in form (positions, sign)

    """
    shifts = []
    w = 20
    w = 160
    d = 80
    csd = to_csd(n, w-d, w)
    # --> csd = [ 0. -1.  0. -1.  0.  0.  0.  0.  0.  0.]
    for i, x in enumerate(csd):
        if x != 0:
            s = w-d-i-1
            shifts.append((s, x>0))
    return shifts


def gen_fblock(M, W, D, name_postfix=""):
    """Generate an FBlock Module.

    :M: Factor-Matrix
    :W: bit width of integers
    :D: decimal bit positions
    :name_postfix: post fix for module names ("fblock"+postfix) (default: "")
    :returns: Module object

    """
    mod = Module("fblock"+name_postfix)
    # Create Inputs
    v = [Integer(width=W, buffer=0, name=f"v{i}") for i in range(M.shape[1])]
    for s in v:
        s._accessed += 1
    z = []
    for y, line in enumerate(M): # Scan matrix lines
        accs = []
        for x, e in enumerate(line): # For entries unequal to 0
            if e != 0:
                shifts = get_shifts(e, W, D) # Extract shifts, signs and positions
                for positions, positive in shifts:
                    print(y, x, positions)
                    if positions < -D:
                        positions = -D
                    v_shifted = v[x].shift(positions=positions)
                    accs.append((v_shifted, positive))
        if len(accs) == 1:
            z.append(accs[0][0])
        if len(accs) == 2: # Generate Additions
            if accs[0][1] and accs[1][1]:
                z.append(accs[0][0].add(accs[1][0]))
            elif accs[0][1] and not accs[1][1]:
                z.append(accs[0][0].sub(accs[1][0]))
            elif not accs[0][1] and accs[1][1]:
                z.append(accs[1][0].sub(accs[0][0]))
            else:
                z.append(accs[0][0].add(accs[1][0]))
        if len(accs) == 3: # Generate Additions
            if accs[0][1] > 0:
                z.append(accs[0][0].add3(accs[1][0], accs[2][0], accs[1][1], accs[2][1]))
            elif accs[1][1] > 0:
                z.append(accs[1][0].add3(accs[0][0], accs[2][0], accs[0][1], accs[2][1]))
            else: 
                z.append(accs[2][0].add3(accs[0][0], accs[1][0], accs[0][1], accs[1][1]))
    return mod


def gen_p2d(Ms, W, D, slice_dims, dim, name="p2d"):
    """Generates a Module for a p2d decomposition (DMP).

    :Ms: matrices in the sliced decomposition (list of slices, each slice list of factors)
    :W: bit width for integers
    :D: number of decimal positions
    :slice_dims: list with slice widths (number of columns for each individual slice)
    :dim: dimension of the original matrix
    :name: name for the module (default: "p2d")
    :returns: list of all created modules, first one is top module

    """
    mod = Module(name)
    # Create inputs
    v = [Integer(width=W, buffer=1) for _ in range(dim[1])]
    zero = Integer.constant(0, W, D)
    v_used = 0
    zs = []
    fblocks = []
    for idx_slice, mats in enumerate(Ms): # For each slice
        # Create (intermediary) vector
        vp = v[v_used:v_used+slice_dims[idx_slice]] + [zero for _ in range(mats[0].shape[1]-slice_dims[idx_slice])]
        v_used += slice_dims[idx_slice]
        for idx_factor, mat in enumerate(mats): # Generate factors
            fblock = gen_fblock(mat, W, D, name_postfix=f"_{name}_{idx_slice}_{idx_factor}")
            fblocks.append(fblock)
            signals = {p[0]: vp[idx_port] for idx_port, p in enumerate(fblock.get_ports()[1])}
            vp = mod.add_module(fblock, signals=signals)
        zs.append(vp)
    for idx in range(dim[0]): # Generate Addertree
        sigs = [z[idx] for z in zs]
        zt = Integer.acc(sigs, tia=False)
        zt.set_buffer(1)
    return [mod] + fblocks


def gen_lzd(D, mats, W, stages=0, print_graph=None, verbose=False):
    """Generates a Module for a lzd decomposition.
    Verbose text output is possible. Generated graphs at different points
    of the creation process are possible.
    Graphs are found under "print_graph".dot and "print_graph_buffer".dot,
    pdf versions are compiled under the corresponding .pdf paths.

    :D: number of decimal positions
    :mats: matrices in the decomposition
    :W: bit width for integers
    :stages: deprecated (default: 0)
    :print_graph: Name of graphs files; if None, no graphs will be created. (Default: None)
    :verbose: True, if extended output shoud be printed to STDOUT (default: False)
    :returns: list of all created modules, first one is top module

    """
    mats, Pj = mats[:-1], mats[-1]
    pr1 = 2
    pr2 = 10
    edges = []
    deps = []
    
    # extract shifts and node depencencies from matrix-factors
    for p, mat in enumerate(mats):
        row = []
        for i, e in enumerate(mat[0]):
            if e != 0:
                shifts = to_csd(e, pr1, pr2)
                for j, b in enumerate(shifts):
                    if b != 0:
                        row.append([p-i+D[0]-1, p+D[0], -1 if e < 0 else 1, pr1-j-1])
        deps.append(row)

    # print statement
    if verbose:
        for l in deps:
            print(l[0][1], l[0][0], l[1][0])
    
    # create graph representation
    if print_graph is not None:
        outstr = []
        for i in range(D[0])[::-1]:
            outstr.append(f"x{i}")
        outstr.append("{ rank=same " + " ".join([f"x{i}" for i in range(D[0])]) + " }")
        for es in deps:
            for a, b,_,_ in es:
                outstr.append(f"x{a} -> x{b}")
            outstr.append("{ rank=same " + f"x{es[0][1]}" + " }")
        f = open(f"{print_graph}.dot", "w")
        f.write("digraph D {\n")
        f.write("\n".join(outstr))
        f.write("\n}")
        f.close()
        os.system(f"dot -Tpdf {print_graph}.dot -o {print_graph}.pdf")
    graph = [[i for i in range(D[0])[::-1]]]

    # print statement
    if verbose:
        for i in graph:
            print(i)
        print()

    # keep track of buffer nodes
    buffers = {}
    def add_buffer(buffer, i, j):
        if i not in buffer:
            buffer[i] = []
        buffer[i].append(j)
        return buffer

    # function to find layer of a node in the graph
    def find_in_graph(graph, i, buffers=None):
        for li, l in enumerate(graph[::-1]):
            if i in l:
                return len(graph)-li-1
            elif buffers is not None:
                for x in buffers:
                    if i in buffers[x]:
                        return len(graph)-li-1


    # find terminal nodes 
    final_nodes = []
    for x, line in enumerate(Pj):
        for y, e in enumerate(line):
            if e != 0:
                final_nodes.append(len(mats)+D[0]-1-y)
            
    # insert all nodes into graph
    for p, layer in enumerate(deps):
        x = max([find_in_graph(graph, e[0], buffers) for e in layer])
        while x+1 >= len(graph):
            graph.append([])
        graph[x+1].append(p+D[0])
    edges = []
    nn = len(mats)+D[0]

    # insert new final nodes iff required (not in last layer)
    for i in range(D[1]):
        fn = final_nodes[i]
        if not (fn in graph[-1]):
            graph[-1].append(nn)
            deps.append([[fn, nn]])
            final_nodes[i] = nn
            nn += 1

    # create list of edges and insert buffers
    for p, layer in enumerate(deps):
        for e in layer:
            a = find_in_graph(graph, e[0])
            b = find_in_graph(graph, e[1])
            na = e[0]
            ne = e[1]
            add_last_edge = True
            for i in range(b-1, a, -1):
                if na in buffers:
                    bufs = [x for x in buffers[e[0]] if find_in_graph(graph, x) == i]
                    if len(bufs) > 0:
                        edges.append([bufs[0], ne])
                        add_last_edge = False
                        break
                graph[i].append(nn)
                edges.append([nn, ne])
                ne = nn
                buffers = add_buffer(buffers, na, nn)
                nn += 1
            if add_last_edge:
                edges.append([na, ne])
    
    # print statement
    if verbose:
        for e in edges:
            print(e)

    # create buffered graph representation
    def buffer_node(x):
        for y in buffers:
            if x in buffers[y]:
                return True
        return False

    if print_graph is not None:

        # find critical path
        critical_paths = [[i] for i in graph[-1]]
        for i in range(len(graph)-1):
            ncps = []
            for cp in critical_paths:
                es = [x for x in edges if x[1] == cp[-1]]
                for n,_ in es:
                    if not buffer_node(n):
                        ncps.append(cp+[n])
            critical_paths = ncps
        critical_paths = {x for path in critical_paths for x in path}
        print(critical_paths)

        outstr = []
        for height, layer in enumerate(graph):
            for li, e in enumerate(layer):
                if e < D[0]:
                    outstr.append(f"x{e} [color=black, shape=invtriangle, width=0.8, style=filled, fillcolor=teal, fontcolor=white]")
                elif e in final_nodes:
                    outstr.append(f"x{e} [color=black, shape=invtriangle, width=0.8, style=filled, fillcolor=teal, fontcolor=white]")
                elif buffer_node(e):
                    outstr.append(f"x{e} [label=\"\", color=black, shape=point, width=0.15]")
                elif e in critical_paths:
                    outstr.append(f"x{e} [color=black, style=filled, fillcolor=purple, fontcolor=white]")
                else:
                    outstr.append(f"x{e} [style=filled, fillcolor=grey, fontcolor=black]")
        for e in edges:
            if buffer_node(e[1]):
                outstr.append(f"x{e[0]} -> x{e[1]} [dir=none]")
            else:
                outstr.append(f"x{e[0]} -> x{e[1]}")
        f = open(f"{print_graph}_buffer.dot", "w")
        f.write("digraph D {\n")
        f.write("\n".join(outstr))
        f.write("\n}")
        f.close()
        os.system(f"dot -Tpdf {print_graph}_buffer.dot -o {print_graph}_buffer.pdf")
        exit()
    
    # print statement
    if verbose:
        for layer in graph:
            print(layer)

    # generate architecture
    mod = Module("lzd")
    v = {}
    edge_in = {}
    for n in graph[0]:
        v[n] = Integer(name=f"x{n}", width=W)
    for layer in graph:
        for n in layer:
            edge_in[n] = []
    for e in edges:
        edge_in[e[1]].append(e)
    n = D[0]
    stack = []
    while n in edge_in:
        stack.append(n)
        n += 1
    while len(stack) > 0:
        n, stack = stack[0], stack[1:]
        if len(edge_in[n]) == 1: # assignment
            e0 = edge_in[n][0]
            if e0[0] not in v:
                stack.append(n)
                continue
            v[e0[1]] =v[e0[0]].copy(f"x{n}", mod)
        elif len(edge_in[n]) == 2: # addition
            a = edge_in[n][0]
            b = edge_in[n][1]
            if (a[0] not in v) or (b[0] not in v):
                stack.append(n)
                continue
            ax = v[a[0]].shift(a[3])
            bx = v[b[0]].shift(a[3])
            v[a[1]] = ax.add(bx)

    return mod


def main():
    """Main function to visualize lzd decomposition"""
    Module.OUTPATH = "hdl/"
    d = 12
    D = (d,d)
    M = np.random.rand(*D)*2-1
    print(M)
    max_add = 280
    mats, snr, adds, p = decomp_lzd(D, M, max_add=max_add)
    print(max_add, adds)
    gen_lzd(D, mats, 8, print_graph="graph", stages=2)


if __name__ == "__main__":
    main()
