from collections import defaultdict
from itertools import combinations
from random import Random, randrange
from string import digits
from sys import stdout, stderr
import html
import os.path

from .contest_details import *
from .utils import *
from .iutils import *


class SeatingError(Exception): ...
class SeatingFormatError(SeatingError): ...


script_path = os.path.dirname(os.path.realpath(__file__))

def dump_grid(f, grid):
    sz = max(len(str(v)) for row in grid for v in row)
    for row in grid:
        print(*(str(v).rjust(sz) for v in row), file=f)

class Seating:
    def __init__(self, seating, *constraints):
        self.constraints = constraints
        self.seating = seating
        super(Seating, self).__init__()

    @classmethod
    def load(cls, f):
        grids = []
        f = iter(f)

        eof = False
        while not eof:
            size = None
            grid = []
            while True:
                try:
                    line = next(f)
                except StopIteration:
                    eof = True
                    break
                line = line.strip()
                if line == 'END':
                    eof = True
                    break
                if not line: break
                line = line.split()
                if size is None: size = len(line)
                if size != len(line): raise SeatingFormatError("unequal number of cols")
                grid.append(line)

            if grid:
                grids.append(grid)

        if not grids:
            raise SeatingFormatError("no grids found")
        return Seating(*grids)

    def find_constraints(self, ch):
        for const in self.constraints:
            if any(ch in row for row in const):
                return const

        const = [[ch]]
        self.constraints += const,
        return const

    def dump(self, f):
        grids = (self.seating,) + self.constraints
        sz = max(len(str(v)) for grid in grids for row in grid for v in row)
        for grid in grids:
            for row in grid:
                print(*(str(v).rjust(sz) for v in row), file=f)
            print(file=f)
        print('END', file=f)

    @classmethod
    def gen(cls, r, c=None, w=0):
        if c is None: c = r
        if r <= 0: raise ValueError("Number of rows must be positive")
        if c <= 0: raise ValueError("Number of cols must be positive")
        if w < 0: raise ValueError("Radius must not be negative")

        seating = [['.']*c for i in range(r)]
        box = max(11, 2*w + 3)
        ctr = box // 2
        constraint = [['*' if i == j == ctr else '1' if max(abs(i - ctr), abs(j - ctr)) <= w else '.'
            for j in range(box)]
            for i in range(box)]

        return cls(seating, constraint)

    def assign(self, groups, seedval=None):
        seating = list(map(list, self.seating))
        
        if seedval is None: seedval = randrange(10**6)

        if sum(groups) > sum(ch != '.' for row in seating for ch in row):
            raise SeatingError('More people than seats')

        # prepare
        seats = [(i, j) for i, row in enumerate(seating) for j, ch in enumerate(row) if ch != '.' and ch != '#']

        pair_cost = defaultdict(int)
        dcost = {d: 10**int(d) for d in digits}
        dcost.update({'#': 10**18, '.': 0})
        def bad_pair(x, y, cost):
            for k in [(x, y), (y, x)]:
                pair_cost[k] = max(pair_cost[k], cost)

        for i, j in seats:
            const = self.find_constraints(seating[i][j])
            [(pi, pj)] = [(ci, cj) for ci, row in enumerate(const) for cj, ch in enumerate(row) if ch == seating[i][j]]
            for ai in range(len(const)):
                for aj in range(len(const[ai])):
                    if const[ai][aj] != seating[i][j]:
                        ni = i + ai - pi
                        nj = j + aj - pj
                        if 0 <= ni < len(seating) and 0 <= nj < len(seating[ni]):
                            bad_pair((i, j), (ni, nj), dcost[const[ai][aj]])
        
        # attempts begin
        best_assignment = None
        best_cost = float('inf')
        best_sid = None
        IT = 1111
        for it in range(IT):
            sid = seedval ^ it**2
            assignment, cost = attempt_assignment(sid, seats, pair_cost, groups)
            if best_cost > cost:
                best_cost = cost
                best_assignment = assignment
                best_sid = sid
                print('Got a badness of', cost, file=stderr)
                if best_cost == 0:
                    print("We're done!", file=stderr)
                    break

        # TODO construct the grid here
        grid = [['.']*len(row) for row in seating]
        for i, j in seats:
            grid[i][j] = '*'

        for i in range(len(grid)):
            for j in range(len(grid[i])):
                if seating[i][j] == '#':
                    grid[i][j] = '#'

        for gr, (i, j) in best_assignment:
            grid[i][j] = gr
        return grid, best_sid

    def write(self, team_schools, targetfile, seedval=None, **context):
        group_teams = [ts['teams'] for ts in team_schools]

        grid, seed = self.assign(list(map(len, group_teams)), seedval=seedval)

        rand = Random(seed) # lol reuse seed

        for teams in group_teams: rand.shuffle(teams)

        school_of_team = {team: ts['school'] for ts in team_schools for team in ts['teams']}

        # TODO maybe use some jinja/django templating here...
        def make_table():
            seat = 0
            for i in range(len(grid)):
                yield "    <tr>"
                for j in range(len(grid[i])):
                    if isinstance(grid[i][j], int):
                        assert 0 <= grid[i][j] < len(group_teams)
                        team_name = group_teams[grid[i][j]].pop()
                        school_name = school_of_team[team_name]
                        if isinstance(school_name, int): school_name = ''
                        yield """
                                <td class='fullcol info' style='vertical-align: middle; text-align: center; line-height: 1.2'>
                                <!-- -->
                                        <span style='font-size: 70%'>{seat}</span>
                                    <br><span style='font-size: 72%'><strong>{team_name}</strong></span>
                                    <br><emph><span style='font-size: 52%'>{school_name}</span></emph></td>
                                <!-- -->
                                <!--
                                <span style='font-size: 70%'>{seat}</span>
                                <br><emph><span style='font-size: 100%'>{school_name}</span></emph></td>
                                <!-- -->
                                """.format(
                                seat='Seat no. {}'.format(seat),
                                team_name=html.escape(team_name),
                                school_name=html.escape(school_name),
                            )
                        seat += 1
                    elif grid[i][j] in {'*', '#'}:
                        yield "        <td class='fullcol active'><small>{seat}</small></td>".format(
                                seat='({})'.format(seat),
                            )
                        seat += 1
                    else:
                        assert grid[i][j] == '.'
                        yield "        <td class='emptycol'><small>&nbsp;</small></td>"
                yield "    </tr>"

        context.update({
            "seedval": ' or '.join({str(x) for x in [seedval, seed] if x is not None}),
            "table": '\n'.join(make_table()),
        })

        # TODO maybe use some jinja/django templating here...
        if not context.get('code'): context['code'] = ''
        if not context.get('title'): context['title'] = ''
        context['for_code'] = 'FOR {}'.format(context['code']) if context['code'] else ''
        context['for_title'] = 'FOR {}'.format(context['title']) if context['title'] else ''
        context['code'] = '(' + context['code'] + ')' if context['code'] else ''
        context['ptitle'] = '(' + context['title'] + ')' if context['title'] else ''
        with open(os.path.join(script_path, 'data', 'seating.html')) as of:
            targetfile.write(of.read().format(**context))


def attempt_assignment(seed, nodes, edge_cost, groups):
    assert sum(groups) <= len(nodes)
    rand = Random(seed ^ 0xC0FFEEF1ED)

    def group_seq():
        for idx, ct in enumerate(groups):
            for it in range(ct):
                yield idx

    in_group = {}
    group_of = [None]*sum(groups)
    for i, g in enumerate(group_seq()):
        in_group.setdefault(g, []).append(i)
        group_of[i] = g

    assert all(x is not None for x in group_of)

    node_of = list(nodes)
    rand.shuffle(node_of)
    node_of = node_of[:sum(groups)]

    # perturb costs
    nedge_cost = defaultdict(int)
    nedge_cost.update({e: c + rand.random() * 1e-4 for e, c in edge_cost.items()})
    def get_cost(costs=nedge_cost):
        return sum(costs[node_of[i], node_of[j]] for gr in in_group.values() for i, j in combinations(gr, 2))

    best_cost = get_cost()
    IT = 1111
    for it in range(IT):
        # rand swap
        ii = rand.randrange(len(node_of))
        jj = rand.randrange(len(node_of))
        node_of[ii], node_of[jj] = node_of[jj], node_of[ii]

        cost = get_cost()
        if best_cost > cost:
            best_cost = cost
            if best_cost < 1: break # found optimal
        else:
            # return swap
            node_of[ii], node_of[jj] = node_of[jj], node_of[ii]

    return list(zip(group_of, node_of)), get_cost(edge_cost)

def compactify(const):
    li = lj = float('+inf')
    ri = rj = float('-inf')
    for (i, j), ch in const.items():
        d = ch != '.'
        li = min(li, i - d)
        lj = min(lj, j - d)
        ri = max(ri, i + d)
        rj = max(rj, j + d)

    assert li <= ri
    assert lj <= rj

    grid = [[0]*(rj - lj + 1) for it in range(ri - li + 1)]
    for i in range(li, ri + 1):
        for j in range(lj, rj + 1):
            grid[i - li][j - lj] = const.get((i, j), '.')

    return grid


def write_seating(contest, seedval=None, dest='.'):

    with open(contest.seating) as f: seating = Seating.load(f)

    if seedval is None: seedval = randrange(10**6)

    filename = os.path.join(dest, 'seating_{}.html').format(contest.code)
    print("Writing to", filename, file=stderr)
    with open(filename, 'w') as f:
        seating.write(contest.team_schools, f, seedval, code=contest.code, title=contest.title)


def seating_args(seating_p):
    seating_p.add_argument('seating_file', help='seating file')
    subparsers = seating_p.add_subparsers(help='which operation to perform', dest='operation')
    subparsers.required = True

    gen_p = subparsers.add_parser('gen', help='Generate a template seating arrangement file')
    gen_p.add_argument('rows', type=int, help='number of rows')
    gen_p.add_argument('cols', type=int, help='number of columns')
    gen_p.add_argument('width', type=int, nargs='?', default=0, help='how far to disallow seating same-school students')

    @set_handler(gen_p)
    def kg_seating_gen(format_, args):
        print('Making a {} x {} grid with seating width {}...'.format(args.rows, args.cols, args.width))
        seating = Seating.gen(args.rows, args.cols, args.width)
        with open(args.seating_file, 'w') as f: seating.dump(f)


    set_p = subparsers.add_parser('set', help='Set a range of values in the seating arrangement to a character')
    set_p.add_argument('char', help='Character to write')
    set_p.add_argument('rows', help='t-sequence of rows')
    set_p.add_argument('cols', help='t-sequence of columns')

    @set_handler(set_p)
    def kg_seating_set(format_, args):
        with open(args.seating_file) as f: seating = Seating.load(f)

        ch = args.char
        if ch in digits: raise ValueError("Cannot write digits in seating grid: {}".format(ch))
        rowr = t_sequence_ranges(args.rows)
        colr = t_sequence_ranges(args.cols)
        written = 0
        for i in range(len(seating.seating)):
            if any(i in rg for rg in rowr):
                for j in range(len(seating.seating[i])):
                    if any(j in rg for rg in colr):
                        seating.seating[i][j] = ch

        with open(args.seating_file, 'w') as f: seating.dump(f)


    force_p = subparsers.add_parser('force', help='Add or remove constraints for a certain character')
    force_p.add_argument('char', help='Character to add constraint to')
    force_p.add_argument('power', help='What to write. Must be a digit or "."')
    force_p.add_argument('-d', '--dirs', nargs='+', help='Directions to write to', required=True)
    force_p.add_argument('-v', '--values', type=int, nargs='+', help='Sequence of values', required=True)

    dirmove = {
        'U': (-1, 0),
        'D': (+1, 0),
        'L': (0, -1),
        'R': (0, +1),
        '': (0, 0),
    }
    def add(ab, cd):
        (a, b), (c, d) = ab, cd
        return a + c, b + d

    @set_handler(force_p)
    def kg_seating_force(format_, args):
        with open(args.seating_file) as f: seating = Seating.load(f)

        if args.power not in (digits + '.#'): raise ValueError("Power must be a digit, #, or dot. {}".format(args.power))
        const = defaultdict()
        gconst = seating.find_constraints(args.char)
        for i in range(len(gconst)):
            for j in range(len(gconst[i])):
                const[i, j] = gconst[i][j]


        [start] = [pos for pos, val in const.items() if val == args.char]
        for d in args.dirs:
            walk = dirmove[d[0]]
            sunod = dirmove[d[1:]]
            pos = start
            for v in args.values:
                if v < 0: raise ValueError("Walk values must not be negative")
                cpos = pos
                for it in range(v + 1):
                    if const.get(cpos) != args.char:
                        const[cpos] = args.power
                    cpos = add(cpos, walk)
                pos = add(pos, sunod)

        gconst[:] = compactify(const)

        with open(args.seating_file, 'w') as f: seating.dump(f)


    assign_p = subparsers.add_parser('assign', help='Assign seats to groups')
    assign_p.add_argument('groups', nargs='+', help='Group data')

    @set_handler(assign_p)
    def kg_seating_assign(format_, args):
        with open(args.seating_file) as f: seating = Seating.load(f)

        groups = []
        for g in args.groups:
            gr, ct = map(int, g.split(','))
            groups += ct * [gr]

        grid, sid = seating.assign(groups)

        print('FINAL GRID (seed={}):'.format(sid), file=stderr)
        sz = max(len(str(v)) for row in grid for v in row)
        for row in grid:
            print(*(str(v).rjust(sz) for v in row))


    write_p = subparsers.add_parser('write', help='Assign seats to a list of teams')
    write_p.add_argument('teams', help='JSON file containing the team and school details')
    write_p.add_argument('-s', '--seed', type=int, help='Initial seed to use')
    write_p.add_argument('-c', '--code', '--contest-code', help='Contest code')
    write_p.add_argument('-t', '--title', '--contest-title', help='Contest title')

    @set_handler(write_p, stderr)
    def kg_seating_write(format_, args):
        with open(args.seating_file) as f: seating = Seating.load(f)
        with open(args.teams) as f: team_schools = ContestDetails.get_team_schools(json.load(f))

        print(file=stderr)
        print('.'*30, file=stderr)
        print('Writing the seating arrangement to stdout... Pipe the output to a file if you wish.', file=stderr)
        print('.'*30, file=stderr)
        print(file=stderr)

        seating.write(team_schools, stdout, seedval=args.seed, code=args.code, title=args.title)

        print(file=stderr)
        print('.'*30, file=stderr)
        print('Done writing the seating arrangement to stdout. Pipe the output to a file if you wish.', file=stderr)
        print('.'*30, file=stderr)
        print(file=stderr)
