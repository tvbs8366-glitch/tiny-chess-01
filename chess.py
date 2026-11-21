# Tiny chess engine for make.fun tiny-chess-01 (MIT).
# 0x88 board, alpha-beta + transposition table + quiescence,
# fixed node budget per move (no clock, so replays match).
import json, os, random, urllib.error, urllib.request
ENV_URL = os.environ["MAKEFUN_ENV_URL"]
BD = 60000
MATE = 100000
INF = 1000000
VAL = (0, 100, 320, 330, 500, 900, 0)
PAWN = 'KKKKLMMGLJIKKKKOLLMPMMOQUUUUKKKK'
KNIGHT='ACEECGKKEKMNELNOEKNOELMNCGKLACEE'
BISHOP = 'GIIIIKKKIKLMILLMIKMMIMMMILKKGIII'
ROOK = 'KKKKLMMMJKKKJKKKJKKKJKKKJKKKKKKL'
KING_MG = 'ECCAECCAECCAECCAGEECIGGGOOKKOQMK'
def _dec(s):
    t = []
    for r in range(8):
        row = [(ord(c) - 75) * 5 for c in s[r * 4:(r + 1) * 4]]
        t += row + row[::-1]
    return t
PST = ((), _dec(PAWN), _dec(KNIGHT), _dec(BISHOP), _dec(ROOK), (0,) * 64, ())
KING_MG = _dec(KING_MG)
KN = (-33, -31, -18, -14, 14, 18, 31, 33)
KI = (-17, -16, -15, -1, 1, 15, 16, 17)
DG = (-17, -15, 15, 17)
OR = (-16, -1, 1, 16)
PC = {c: (i % 6 + 1) * (-1 if i < 6 else 1) for i, c in enumerate("pnbrqkPNBRQK")}
PR = "  nbrq"
SQS = tuple(r * 16 + f for r in range(8) for f in range(8))
CASTLE = ((1, 1, 4, 6), (1, 2, 4, 2), (-1, 4, 116, 118), (-1, 8, 116, 114))
_g = random.Random(20261120).getrandbits
ZOB = [[_g(64) for _ in range(128)] for _ in range(12)]
ZS, ZC, ZE = _g(64), [_g(64) for _ in range(16)], [_g(64) for _ in range(8)]
def zi(p):
    return p - 1 if p > 0 else 5 - p
class B:
    def fen(self, fen):
        parts = fen.split()
        rows = parts[0].split("/")
        self.b = [0] * 128
        for r, row in enumerate(rows):
            rank = 7 - r
            f = 0
            for ch in row:
                if ch.isdigit():
                    f += int(ch)
                else:
                    self.b[rank * 16 + f] = PC[ch]
                    f += 1
        self.t = 1 if parts[1] == "w" else -1
        self.c = sum(1 << "KQkq".index(c) for c in parts[2] if c in "KQkq")
        self.e = -1
        if parts[3] != "-":
            self.e = (int(parts[3][1]) - 1) * 16 + (ord(parts[3][0]) - 97)
        self.k = (self.b.index(6), self.b.index(-6))
        self.s = []
        h = 0
        for sq in SQS:
            p = self.b[sq]
            if p:
                h ^= ZOB[zi(p)][sq]
        if self.t == -1:
            h ^= ZS
        h ^= ZC[self.c]
        if self.e >= 0:
            h ^= ZE[self.e & 7]
        self.h = h
    def atk(self, sq, by):
        b = self.b
        for o in ((-15, -17) if by == 1 else (15, 17)):
            t = sq + o
            if not t & 0x88 and b[t] == by:
                return True
        for offs, v in ((KN, 2), (KI, 6)):
            for o in offs:
                t = sq + o
                if not t & 0x88 and b[t] == v * by:
                    return True
        for offs, v in ((DG, 3), (OR, 4)):
            for o in offs:
                t = sq + o
                while not t & 0x88:
                    p = b[t]
                    if p:
                        if p == v * by or p == 5 * by:
                            return True
                        break
                    t += o
        return False
    def gen(self, caps_only=False):
        b = self.b
        turn = self.t
        moves = []
        for sq in SQS:
            p = b[sq]
            if p == 0 or (p > 0) != (turn == 1):
                continue
            a = abs(p)
            if a == 1:
                d = 16 * turn
                one = sq + d
                if not one & 0x88 and b[one] == 0:
                    if (one >> 4) == (7 if turn == 1 else 0):
                        moves += [sq | one << 7 | pp << 14 for pp in (5, 4, 3, 2)]
                    elif not caps_only:
                        moves.append(sq | one << 7)
                        if (sq >> 4) == (1 if turn == 1 else 6):
                            two = sq + 2 * d
                            if b[two] == 0:
                                moves.append(sq | two << 7)
                for dd in (d - 1, d + 1):
                    t = sq + dd
                    if t & 0x88:
                        continue
                    q = b[t]
                    if q != 0 and (q > 0) != (turn == 1):
                        if (t >> 4) == (7 if turn == 1 else 0):
                            moves += [sq | t << 7 | pp << 14 for pp in (5, 4, 3, 2)]
                        else:
                            moves.append(sq | t << 7)
                    elif t == self.e and b[t] == 0:
                        moves.append(sq | t << 7)
            elif a == 2 or a == 6:
                for o in KN if a == 2 else KI:
                    t = sq + o
                    if t & 0x88:
                        continue
                    q = b[t]
                    if q == 0:
                        if not caps_only:
                            moves.append(sq | t << 7)
                    elif (q > 0) != (turn == 1):
                        moves.append(sq | t << 7)
            else:
                for o in DG if a == 3 else OR if a == 4 else DG + OR:
                    t = sq + o
                    while not t & 0x88:
                        q = b[t]
                        if q == 0:
                            if not caps_only:
                                moves.append(sq | t << 7)
                        else:
                            if (q > 0) != (turn == 1):
                                moves.append(sq | t << 7)
                            break
                        t += o
        if not caps_only:
            for tn, bit, kf, kt in CASTLE:
                d = 1 if kt > kf else -1
                rf = kf + 3 if d == 1 else kf - 4
                emp = (kf + d, kf + 2 * d) if d == 1 else (kf + d, kf + 2 * d, kf + 3 * d)
                saf = (kf, kf + d, kf + 2 * d)
                if tn == turn and self.c & bit and b[rf] == 4 * tn \
                        and all(b[s] == 0 for s in emp) \
                        and all(not self.atk(s, -tn) for s in saf):
                    moves.append(kf | kt << 7)
        return moves
    def leg(self):
        out = []
        for m in self.gen():
            self.make(m)
            if not self.atk(self.k[0 if -self.t == 1 else 1], self.t):
                out.append(m)
            self.unmake()
        return out
    def make(self, m):
        b = self.b
        f = m & 127
        t = (m >> 7) & 127
        pr = (m >> 14) & 7
        piece = b[f]
        cap = b[t]
        ec = -1
        oc, oe, oh, ok = self.c, self.e, self.h, self.k
        self.h ^= ZOB[zi(piece)][f]
        if cap:
            self.h ^= ZOB[zi(cap)][t]
        self.h ^= ZC[self.c]
        if self.e >= 0:
            self.h ^= ZE[self.e & 7]
        self.h ^= ZS
        b[t] = piece
        b[f] = 0
        self.h ^= ZOB[zi(piece)][t]
        if abs(piece) == 1:
            if t == oe and cap == 0:
                ec = t - 16 if piece == 1 else t + 16
                cap = b[ec]
                b[ec] = 0
                self.h ^= ZOB[zi(cap)][ec]
            self.e = (f + t) // 2 if abs(t - f) == 32 else -1
            if pr:
                self.h ^= ZOB[zi(piece)][t]
                b[t] = pr if piece == 1 else -pr
                self.h ^= ZOB[zi(b[t])][t]
        else:
            self.e = -1
        if abs(piece) == 6:
            self.k = (t, self.k[1]) if piece == 6 else (self.k[0], t)
            self.c &= ~(1 | 2) if piece == 6 else ~(4 | 8)
            if t - f == 2:
                b[f + 1] = b[f + 3]
                b[f + 3] = 0
                self.h ^= ZOB[zi(b[f + 1])][f + 1] ^ ZOB[zi(b[f + 1])][f + 3]
            elif f - t == 2:
                b[f - 1] = b[f - 4]
                b[f - 4] = 0
                self.h ^= ZOB[zi(b[f - 1])][f - 1] ^ ZOB[zi(b[f - 1])][f - 4]
        else:
            for sq, bit in ((0, 2), (7, 1), (112, 8), (119, 4)):
                if f == sq or t == sq:
                    self.c &= ~bit
        if self.e >= 0:
            self.h ^= ZE[self.e & 7]
        self.h ^= ZC[self.c]
        self.t = -self.t
        self.s.append((m, cap, ec, oc, oe, oh, ok))
    def unmake(self):
        m, cap, ec, oc, oe, oh, ok = self.s.pop()
        b = self.b
        f = m & 127
        t = (m >> 7) & 127
        pr = (m >> 14) & 7
        piece = b[t]
        if pr:
            piece = 1 if piece > 0 else -1
        b[f] = piece
        b[t] = 0
        if ec >= 0:
            b[ec] = cap
        elif cap:
            b[t] = cap
        if abs(piece) == 6:
            if t - f == 2:
                b[f + 3] = b[f + 1]
                b[f + 1] = 0
            elif f - t == 2:
                b[f - 4] = b[f - 1]
                b[f - 1] = 0
        self.t = -self.t
        self.c = oc
        self.e = oe
        self.h = oh
        self.k = ok
    def nul(self):
        self.s.append((-1, 0, -1, self.c, self.e, self.h, self.k))
        self.h ^= ZS
        if self.e >= 0:
            self.h ^= ZE[self.e & 7]
        self.e = -1
        self.t = -self.t
    def unn(self):
        _, _, _, oc, oe, oh, ok = self.s.pop()
        self.t = -self.t
        self.c = oc
        self.e = oe
        self.h = oh
        self.k = ok
    def ev(self):
        b = self.b
        s = 0
        wk = bk = 0
        for sq in SQS:
            p = b[sq]
            if p == 0:
                continue
            a = abs(p)
            i = (sq >> 4) * 8 + (sq & 7)
            if a == 6:
                if p == 6:
                    wk = i
                else:
                    bk = i
                continue
            v = VAL[a] + PST[a][i if p > 0 else i ^ 56]
            s += v if p > 0 else -v
        r = s + KING_MG[wk] - KING_MG[bk ^ 56]
        return r if self.t == 1 else -r
TT = {}
KL = {}
HS = {}
ND = 0
def odr(bd, moves, tt, ply):
    sc = []
    for m in moves:
        t = (m >> 7) & 127
        cap = bd.b[t]
        if cap == 0 and t == bd.e and abs(bd.b[m & 127]) == 1:
            cap = -bd.t
        s = 0
        if m == tt:
            s = 1000000
        elif cap:
            s = 10000 + 10 * VAL[abs(cap)] - VAL[abs(bd.b[m & 127])] // 16
        elif KL.get((ply, 0)) == m or KL.get((ply, 1)) == m:
            s = 9000
        else:
            s = HS.get((bd.b[m & 127], t), 0)
        sc.append((-s, m))
    sc.sort()
    return [m for _, m in sc]
def qs(bd, al, be, ply):
    global ND
    ND += 1
    if ND > BD:
        raise TimeoutError
    if ply > 32:
        return al
    chk = bd.atk(bd.k[0 if bd.t == 1 else 1], -bd.t)
    if not chk:
        st = bd.ev()
        if st >= be:
            return be
        if st > al:
            al = st
    legal = 0
    for m in odr(bd, bd.gen(caps_only=not chk), 0, ply):
        bd.make(m)
        if bd.atk(bd.k[0 if -bd.t == 1 else 1], bd.t):
            bd.unmake()
            continue
        legal += 1
        sc = -qs(bd, -be, -al, ply + 1)
        bd.unmake()
        if sc >= be:
            return be
        if sc > al:
            al = sc
    if legal == 0:
        return -MATE + ply if chk else al
    return al
def sr(bd, d, al, be, ply, gh):
    global ND
    ND += 1
    if ND > BD:
        raise TimeoutError
    if gh.get(bd.h, 0) >= 2:
        return 0
    if d <= 0:
        return qs(bd, al, be, ply)
    e = TT.get(bd.h)
    tt = 0
    if e and e[0] >= d:
        sc, fl, mv = e[1], e[2], e[3]
        if fl == 0:
            return sc
        if fl == 1 and sc >= be:
            return sc
        if fl == 2 and sc <= al:
            return sc
        tt = mv
    if d >= 3 and not bd.atk(bd.k[0 if bd.t == 1 else 1], -bd.t) and bd.ev() >= be:
        bd.nul()
        sc = -sr(bd, d - 3, -be, -be + 1, ply + 1, gh)
        bd.unn()
        if sc >= be:
            return be
    legal = 0
    best = -INF
    bm = 0
    fl = 2
    for m in odr(bd, bd.gen(), tt, ply):
        bd.make(m)
        if bd.atk(bd.k[0 if -bd.t == 1 else 1], bd.t):
            bd.unmake()
            continue
        legal += 1
        sc = -sr(bd, d - 1, -be, -al, ply + 1, gh)
        bd.unmake()
        if sc > best:
            best = sc
            bm = m
        if sc > al:
            al = sc
            fl = 0
        if al >= be:
            fl = 1
            if not bd.b[(m >> 7) & 127]:
                if KL.get((ply, 0)) != m:
                    KL[(ply, 1)] = KL.get((ply, 0), 0)
                    KL[(ply, 0)] = m
                HS[(bd.b[m & 127], (m >> 7) & 127)] = \
                    HS.get((bd.b[m & 127], (m >> 7) & 127), 0) + d * d
            break
    if legal == 0:
        return -MATE + ply if bd.atk(bd.k[0 if bd.t == 1 else 1], -bd.t) else 0
    if abs(best) < 99000:
        TT[bd.h] = (d, best, fl, bm)
    return best
def uci(m):
    f = m & 127
    t = (m >> 7) & 127
    s = "abcdefgh"[f & 7] + str((f >> 4) + 1) + "abcdefgh"[t & 7] + str((t >> 4) + 1)
    pr = (m >> 14) & 7
    return s + (PR[pr] if pr else "")
def ch(bd, legal_uci, gh):
    global ND
    moves = bd.leg()
    by_uci = {uci(m): m for m in moves}
    if set(by_uci) != set(legal_uci):
        return gr(bd, legal_uci)
    best = moves[0]
    depth = 1
    ND = 0
    while depth <= 40:
        try:
            cur = None
            cs = -INF
            al = -INF
            for m in odr(bd, moves, 0, 0):
                bd.make(m)
                sc = -sr(bd, depth - 1, -INF, -al, 1, gh)
                bd.unmake()
                if sc > cs:
                    cs = sc
                    cur = m
                if sc > al:
                    al = sc
            if cur is not None:
                best = cur
            depth += 1
        except TimeoutError:
            break
    return uci(best)
def gr(bd, lu):
    return min(lu, key=lambda u: (-(VAL[abs(bd.b[(ord(u[2]) - 97) + (int(u[3]) - 1) * 16])] if bd.b[(ord(u[2]) - 97) + (int(u[3]) - 1) * 16] else 0), -(900 if len(u) == 5 and u[4] == "q" else 0), u))
def post(path, body):
    req = urllib.request.Request(ENV_URL + path, data=json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.code)
def main():
    bd = B()
    gh = {}
    last = -1
    while True:
        g = post("/game", {})
        if g.get("status") == "done":
            break
        if g["game"] != last:
            last = g["game"]
            gh = {}
        while g.get("status") == "your_move":
            bd.fen(g["fen"])
            gh[bd.h] = gh.get(bd.h, 0) + 1
            try:
                move = ch(bd, g["legal_moves"], gh)
            except Exception:
                move = gr(bd, g["legal_moves"])
            try:
                g = post("/move", {"game": g["game"], "move": move})
            except RuntimeError:
                rest = [u for u in g["legal_moves"] if u != move]
                g = post("/resign", {"game": g["game"]}) if not rest else post("/move", {"game": g["game"], "move": gr(bd, rest)})
if __name__ == "__main__":
    main()
