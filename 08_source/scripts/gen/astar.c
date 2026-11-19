/* A* 8 hướng có trạng thái hướng cho bộ đi dây (xem rt_core.py).
   Biên dịch:  gcc -O2 -shared -fPIC -o astar.so astar.c
   Trạng thái = (lớp, ô, hướng); hướng 0..7, 8 = tự do (điểm đầu hoặc vừa qua via). */
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const int DX[8] = {1, 1, 0, -1, -1, -1, 0, 1};
static const int DY[8] = {0, 1, 1, 1, 0, -1, -1, -1};

typedef struct { float f; float g; long s; } HN;
typedef struct { HN *a; long n, cap; } Heap;

static void hpush(Heap *h, float f, float g, long s) {
    if (h->n == h->cap) { h->cap = h->cap ? h->cap * 2 : 4096; h->a = (HN *)realloc(h->a, h->cap * sizeof(HN)); }
    long i = h->n++;
    while (i > 0) {
        long p = (i - 1) >> 1;
        if (h->a[p].f <= f) break;
        h->a[i] = h->a[p]; i = p;
    }
    h->a[i].f = f; h->a[i].g = g; h->a[i].s = s;
}
static HN hpop(Heap *h) {
    HN top = h->a[0];
    HN last = h->a[--h->n];
    long i = 0;
    for (;;) {
        long c = 2 * i + 1;
        if (c >= h->n) break;
        if (c + 1 < h->n && h->a[c + 1].f < h->a[c].f) c++;
        if (h->a[c].f >= last.f) break;
        h->a[i] = h->a[c]; i = c;
    }
    h->a[i] = last;
    return top;
}

/* par: bit0-3 hướng trước, bit4-5 lớp trước, bit6-7 loại (0 bước, 1 via, 2 via cặp, 3 điểm đầu) */
long astar(int nxw, int nyw, const unsigned char *b0, const unsigned char *b1, const unsigned char *b2,
           const unsigned char *g0, const unsigned char *g1, const unsigned char *g2, const float *h,
           const int *starts, int nstarts, int step, const float *lw, float via_cost,
           const unsigned char *viablk, int gdir, int pairvia, float turn, float hw, long maxexp,
           int minrun, int *out, long outcap) {
    const unsigned char *blk[3] = {b0, b1, b2};
    const unsigned char *goal[3] = {g0, g1, g2};
    long N = (long)nxw * nyw;
    long NS = 3 * N * 9;
    float *best = (float *)malloc(NS * sizeof(float));
    unsigned char *par = (unsigned char *)malloc(NS);
    unsigned char *nst = (unsigned char *)calloc(NS, 1);
    if (!best || !par || !nst) { free(best); free(par); free(nst); return -2; }
    for (long i = 0; i < NS; i++) best[i] = 1e30f;
    Heap hp = {0, 0, 0};
    for (int i = 0; i < nstarts; i++) {
        int li = starts[4 * i], x = starts[4 * i + 1], y = starts[4 * i + 2], d = starts[4 * i + 3];
        if (!blk[li] || x < 0 || y < 0 || x >= nxw || y >= nyw) continue;
        long idx = (long)y * nxw + x;
        long s = (li * N + idx) * 9 + d;
        best[s] = 0; par[s] = 3 << 6;
        hpush(&hp, h[idx] * 10 * hw, 0, s);
    }
    long nexp = 0, found = -1;
    while (hp.n) {
        HN t = hpop(&hp);
        long s = t.s;
        float g = t.g;
        if (g > best[s]) continue;
        int d = (int)(s % 9);
        long c = s / 9;
        int li = (int)(c / N);
        long idx = c - li * N;
        if (goal[li] && goal[li][idx] && (gdir < 0 || d == gdir) && g > 0) { found = s; break; }
        if (++nexp > maxexp) break;
        int y = (int)(idx / nxw), x = (int)(idx - (long)y * nxw);
        const unsigned char *b = blk[li];
        float w = lw[li];
        int lo = (d == 8) ? 0 : -1, hi = (d == 8) ? 7 : 1;
        for (int k = lo; k <= hi; k++) {
            int nd = (d == 8) ? k : ((d + k) & 7);
            int turning = !(nd == d || d == 8);
            int run = (turning && minrun > 1) ? minrun : 1;      /* rẽ hướng: đi liền `run` bước theo hướng mới */
            int x2 = x, y2 = y, ok = 1, steps = 0;
            for (int j = 1; j <= run; j++) {
                int xn = x2 + DX[nd] * step, yn = y2 + DY[nd] * step;
                if (xn < 0 || yn < 0 || xn >= nxw || yn >= nyw) { ok = 0; break; }
                if (b[(long)yn * nxw + xn]) { ok = 0; break; }
                if (step == 2 && b[(long)(y2 + DY[nd]) * nxw + x2 + DX[nd]]) { ok = 0; break; }
                x2 = xn; y2 = yn; steps = j;
                if (gdir < 0 && goal[li] && goal[li][(long)y2 * nxw + x2]) break;   /* chạm đích giữa chừng */
            }
            if (!ok) continue;
            long i2 = (long)y2 * nxw + x2;
            float ng = g + ((nd & 1) ? 14.0f : 10.0f) * step * steps * w + (turning ? turn : 0.0f);
            long s2 = (li * N + i2) * 9 + nd;
            if (ng < best[s2]) {
                best[s2] = ng; par[s2] = (unsigned char)(d | (li << 4)); nst[s2] = (unsigned char)steps;
                hpush(&hp, ng + h[i2] * 10 * hw, ng, s2);
            }
        }
        if (viablk && !pairvia && !viablk[idx]) {
            for (int lj = 0; lj < 3; lj++) {
                if (lj == li || !blk[lj] || blk[lj][idx]) continue;
                long s2 = (lj * N + idx) * 9 + 8;
                float ng = g + via_cost;
                if (ng < best[s2]) {
                    best[s2] = ng; par[s2] = (unsigned char)(d | (li << 4) | (1 << 6));
                    hpush(&hp, ng + h[idx] * 10 * hw, ng, s2);
                }
            }
        }
        if (pairvia && d < 8 && viablk) {
            int xm = x + DX[d] * pairvia, ym = y + DY[d] * pairvia;
            int xe = x + 2 * DX[d] * pairvia, ye = y + 2 * DY[d] * pairvia;
            if (xe >= 0 && ye >= 0 && xe < nxw && ye < nyw && !viablk[(long)ym * nxw + xm]) {
                int ok = 1;
                for (int k = 1; k <= pairvia && ok; k++)
                    if (b[(long)(y + DY[d] * k) * nxw + x + DX[d] * k]) ok = 0;
                if (ok) for (int lj = 0; lj < 3; lj++) {
                    if (lj == li || !blk[lj]) continue;
                    const unsigned char *bj = blk[lj];
                    int ok2 = 1;
                    for (int k = pairvia; k <= 2 * pairvia && ok2; k++)
                        if (bj[(long)(y + DY[d] * k) * nxw + x + DX[d] * k]) ok2 = 0;
                    if (!ok2) continue;
                    long i2 = (long)ye * nxw + xe;
                    long s2 = (lj * N + i2) * 9 + d;
                    float ng = g + via_cost + ((d & 1) ? 14.0f : 10.0f) * 2 * pairvia;
                    if (ng < best[s2]) {
                        best[s2] = ng; par[s2] = (unsigned char)(d | (li << 4) | (2 << 6));
                        hpush(&hp, ng + h[i2] * 10 * hw, ng, s2);
                    }
                }
            }
        }
    }
    long cnt = -1;
    if (found >= 0) {
        cnt = 0;
        long s = found;
        for (;;) {
            int d = (int)(s % 9);
            long c = s / 9;
            int li = (int)(c / N);
            long idx = c - li * N;
            int y = (int)(idx / nxw), x = (int)(idx - (long)y * nxw);
            if (cnt < outcap) { out[3 * cnt] = li; out[3 * cnt + 1] = x; out[3 * cnt + 2] = y; }
            cnt++;
            unsigned char p = par[s];
            int type = p >> 6, pd = p & 15, pl = (p >> 4) & 3;
            if (type == 3) break;
            if (type == 0) { int q = nst[s] ? nst[s] : 1; x -= DX[d] * step * q; y -= DY[d] * step * q; }
            else if (type == 2) { x -= 2 * DX[d] * pairvia; y -= 2 * DY[d] * pairvia; }
            s = (pl * N + (long)y * nxw + x) * 9 + pd;
        }
        if (cnt > outcap) cnt = -3;
    }
    free(best); free(par); free(nst); free(hp.a);
    return cnt;
}
