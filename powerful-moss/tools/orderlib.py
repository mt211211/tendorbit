"""A broad library of orderings for the 12 clock words.

Beyond the 24 rotations and the reading/column/alphabetical orders already
swept, the album itself supplies permutations that were never tried: it has
exactly 12 tracks, matching the 12 hours, so the track list is a candidate
key for the order.
"""
TRACKS = ["GenerativeAdversarialNeurology", "PowerfulMoss", "TooManyBees",
          "EmptyLongWaves", "TempoRare", "DiscomfortMeditation",
          "CurvedHorizon", "DarkForest", "FallingUp", "Cliffside",
          "ShadowRealm", "GravitationalWaveAntennae"]

READ = [12, 11, 1, 10, 2, 9, 3, 8, 4, 7, 5, 6]
COL = [9, 8, 10, 7, 11, 6, 12, 1, 5, 2, 4, 3]


def build():
    out = {}
    for st in range(1, 13):
        out[f'cw@{st}'] = [((st - 1 + k) % 12) + 1 for k in range(12)]
        out[f'ccw@{st}'] = [((st - 1 - k) % 12) + 1 for k in range(12)]
    out['read'] = READ
    out['read_rev'] = READ[::-1]
    out['col'] = COL
    out['col_rev'] = COL[::-1]

    # album order -> alphabetical rank, and its inverse
    alpha = sorted(range(12), key=lambda i: TRACKS[i].lower())
    # alpha[r] = album index (0-based) of the r-th track alphabetically
    a2r = [alpha.index(i) + 1 for i in range(12)]   # album pos -> alpha rank
    r2a = [alpha[r] + 1 for r in range(12)]         # alpha rank -> album pos
    out['track_alpha_rank'] = a2r
    out['track_alpha_rank_rev'] = a2r[::-1]
    out['track_alpha_pos'] = r2a
    out['track_alpha_pos_rev'] = r2a[::-1]

    # by track title length, and by first letter
    bylen = sorted(range(12), key=lambda i: (len(TRACKS[i]), TRACKS[i]))
    out['track_len'] = [i + 1 for i in bylen]
    out['track_len_rev'] = out['track_len'][::-1]
    return out


ORDERS = build()

if __name__ == '__main__':
    for k, v in ORDERS.items():
        print(f'{k:<22} {v}')
    # sanity: every ordering is a permutation of 1..12
    for k, v in ORDERS.items():
        assert sorted(v) == list(range(1, 13)), k
    print(f'\n{len(ORDERS)} orderings, all valid permutations of 1..12')
