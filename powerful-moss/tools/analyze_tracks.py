#!/usr/bin/env python3
"""Powerful Moss - per-track seed-word hunter.

WHY THIS EXISTS
---------------
The author's own description of the album is:

    "A 12-word seed is spread across the 12 tracks of the album.
     Like a clock, year, or seed phrase, this album has 12 of 'em."

So one seed word is hidden per track.  The published dossier instead assumes
the POAP clock image carries all 12 words, and dismisses the audio because the
masters have "close to 0 percent energy above 13 kHz ... no high band left to
carry spectrogram text".  That reasoning only rules out ONE technique.  In the
artist's own solved "Bifurcations" puzzle the words were carried by:

    track 1  a spectrogram image (compass) plus Morse  -> "west"
    track 3  Morse played on the DRUMS: kick = dash, snare = dot, ~1:31
    track 4  an SSTV (Robot 36) payload in the spectrogram
    track 2  spoken digits of the Feigenbaum constant, whose "errors"
             encoded the ORDER of the words

Morse-in-drums and spoken words sit in the audible band.  A silent high band
says nothing about them.  This script therefore sweeps the techniques that
artist has actually used, plus the usual suspects.

USAGE
-----
    pip install numpy scipy matplotlib
    python analyze_tracks.py "C:\\path\\to\\Powerful_Moss"

Writes <dir>/_analysis/ with one spectrogram set per track and prints a
report.  Send the PNGs and the report back for interpretation.

    python analyze_tracks.py --selftest      # certify the detectors
"""
import os, sys, json, wave, argparse, math

import numpy as np

MORSE = {
    '.-': 'a', '-...': 'b', '-.-.': 'c', '-..': 'd', '.': 'e', '..-.': 'f',
    '--.': 'g', '....': 'h', '..': 'i', '.---': 'j', '-.-': 'k', '.-..': 'l',
    '--': 'm', '-.': 'n', '---': 'o', '.--.': 'p', '--.-': 'q', '.-.': 'r',
    '...': 's', '-': 't', '..-': 'u', '...-': 'v', '.--': 'w', '-..-': 'x',
    '-.--': 'y', '--..': 'z',
    '-----': '0', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
    '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',
}


def bip39():
    """the BIP39 English wordlist, from the `mnemonic` package if present"""
    try:
        from mnemonic import Mnemonic
        return set(Mnemonic('english').wordlist)
    except Exception:
        return set()


WORDS = bip39()


# ---------------------------------------------------------------- audio I/O
def read_wav(path):
    """-> (float mono in [-1,1], sample rate, n_channels, sampwidth)"""
    with wave.open(path, 'rb') as w:
        nch, sw, sr, n = w.getnchannels(), w.getsampwidth(), \
            w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 1:
        a = (np.frombuffer(raw, '<u1').astype(np.float32) - 128) / 128.0
    elif sw == 2:
        a = np.frombuffer(raw, '<i2').astype(np.float32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        v = (b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16))
        v = np.where(v & 0x800000, v - (1 << 24), v)
        a = v.astype(np.float32) / 8388608.0
    elif sw == 4:
        a = np.frombuffer(raw, '<i4').astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f'unsupported sample width {sw}')
    if nch > 1:
        a = a.reshape(-1, nch)
        mono = a.mean(axis=1)
        return mono, sr, nch, sw, a
    return a, sr, nch, sw, a.reshape(-1, 1)


def stft(x, sr, nfft=4096, hop=1024):
    win = np.hanning(nfft).astype(np.float32)
    n = 1 + (len(x) - nfft) // hop
    n = max(n, 1)
    out = np.empty((nfft // 2 + 1, n), np.float32)
    for i in range(n):
        seg = x[i * hop:i * hop + nfft]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        out[:, i] = np.abs(np.fft.rfft(seg * win))
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    times = np.arange(n) * hop / sr
    return out, freqs, times


# ------------------------------------------------------------- morse decode
def morse_from_onsets(times, marks, unit=None):
    """marks: list of (t, kind) kind in {'.','-'} -> decoded text"""
    if not marks:
        return ''
    # group into letters/words by inter-onset gaps
    gaps = [marks[i + 1][0] - marks[i][0] for i in range(len(marks) - 1)]
    if not gaps:
        return MORSE.get(marks[0][1], '')
    g = np.array(gaps)
    if unit is None:
        unit = np.median(g)
    letters, cur = [], [marks[0][1]]
    for i, gp in enumerate(gaps):
        if gp > unit * 2.6:
            letters.append(''.join(cur)); cur = []
            if gp > unit * 5.5:
                letters.append(' ')
        cur.append(marks[i + 1][1])
    letters.append(''.join(cur))
    return ''.join(' ' if L == ' ' else MORSE.get(L, '?') for L in letters)


def band_onsets(x, sr, lo, hi, thresh=3.0, min_sep=0.06):
    """onset times + peak energies in a frequency band"""
    S, f, t = stft(x, sr, 2048, 512)
    sel = (f >= lo) & (f <= hi)
    if not sel.any():
        return np.array([]), np.array([])
    env = S[sel].sum(axis=0)
    if env.max() <= 0:
        return np.array([]), np.array([])
    env = env / env.max()
    d = np.diff(env, prepend=env[0])
    d[d < 0] = 0
    med, sd = np.median(d), d.std() or 1e-9
    peaks = []
    last = -1e9
    for i in range(len(d)):
        if d[i] > med + thresh * sd and t[i] - last >= min_sep:
            peaks.append(i); last = t[i]
    return t[peaks], env[peaks]


def drum_morse(x, sr):
    """kick (low) = dash, snare (mid/noise) = dot -- the Bifurcations track-3
    technique.  Returns (decoded, n_marks)."""
    kt, _ = band_onsets(x, sr, 40, 110)
    st, _ = band_onsets(x, sr, 1500, 5000)
    marks = [(t, '-') for t in kt] + [(t, '.') for t in st]
    marks.sort()
    if len(marks) < 3:
        return '', 0
    return morse_from_onsets(None, marks), len(marks)


def tone_morse(x, sr, lo, hi):
    """Morse as a steady tone burst in a band (classic CW)."""
    S, f, t = stft(x, sr, 2048, 256)
    sel = (f >= lo) & (f <= hi)
    if not sel.any():
        return ''
    env = S[sel].sum(axis=0)
    if env.max() <= 0:
        return ''
    env = env / env.max()
    on = env > max(0.25, np.percentile(env, 80))
    if on.sum() < 3:
        return ''
    runs, i = [], 0
    while i < len(on):
        j = i
        while j + 1 < len(on) and on[j + 1] == on[i]:
            j += 1
        runs.append((on[i], t[j] - t[i] + (t[1] - t[0])))
        i = j + 1
    ons = [d for v, d in runs if v]
    if len(ons) < 3:
        return ''
    u = np.percentile(ons, 30)
    marks = [(k, '.' if d < u * 2 else '-') for k, (v, d)
             in enumerate(runs) if v for _ in [0]]
    seq = []
    for v, d in runs:
        if v:
            seq.append('.' if d < u * 2 else '-')
        else:
            seq.append(' ' if d > u * 5 else ('/' if d > u * 2 else ''))
    s = ''.join(seq)
    letters = [L for L in s.replace('/', ' ').split(' ') if L]
    return ''.join(MORSE.get(L, '?') for L in letters)


# ---------------------------------------------------------------- detectors
def sstv_score(x, sr):
    """SSTV uses a 1200 Hz sync and a 1500-2300 Hz scan band."""
    S, f, t = stft(x, sr, 4096, 1024)
    def band(a, b):
        s = (f >= a) & (f <= b)
        return S[s].sum(axis=0) if s.any() else np.zeros(S.shape[1])
    sync, scan, tot = band(1180, 1220), band(1500, 2300), S.sum(axis=0) + 1e-9
    r = (sync + scan) / tot
    best = int(np.argmax(r))
    return float(r.max()), float(t[best])


def dtmf(x, sr):
    lo_f, hi_f = [697, 770, 852, 941], [1209, 1336, 1477, 1633]
    keys = [['1','2','3','A'],['4','5','6','B'],['7','8','9','C'],['*','0','#','D']]
    S, f, t = stft(x, sr, 4096, 2048)
    out = []
    for i in range(S.shape[1]):
        col = S[:, i]
        if col.max() <= 0:
            continue
        def pk(fr):
            j = int(np.argmin(np.abs(f - fr)))
            return col[max(0, j-2):j+3].max()
        a = [pk(v) for v in lo_f]; b = [pk(v) for v in hi_f]
        ia, ib = int(np.argmax(a)), int(np.argmax(b))
        if a[ia] > col.mean() * 12 and b[ib] > col.mean() * 12:
            out.append((float(t[i]), keys[ia][ib]))
    ded, last = [], None
    for tt, k in out:
        if last is None or k != last[1] or tt - last[0] > 0.25:
            ded.append((tt, k))
        last = (tt, k)
    return ded


def lsb_text(raw_channels, sw):
    """least-significant-bit payload across samples -> printable runs"""
    if sw < 2:
        return []
    ints = np.round(raw_channels[:, 0] * (2 ** (8 * sw - 1))).astype(np.int64)
    bits = (ints & 1).astype(np.uint8)
    out = []
    for order in ('big', 'little'):
        n = len(bits) // 8 * 8
        b = bits[:n].reshape(-1, 8)
        if order == 'little':
            b = b[:, ::-1]
        by = np.packbits(b, axis=1).ravel()
        s = ''.join(chr(c) if 32 <= c < 127 else '\n' for c in by[:400000])
        for run in s.split('\n'):
            if len(run) >= 6:
                out.append((order, run[:120]))
    return out[:40]


def find_words(text):
    if not WORDS or not text:
        return []
    t = ''.join(c if c.isalpha() else ' ' for c in text.lower())
    return sorted({w for w in t.split() if w in WORDS and len(w) >= 3})


def substr_words(text, minlen=4):
    """BIP39 words appearing as substrings of a letter run (morse output has
    no spaces, so whole-token matching misses them)"""
    if not WORDS or not text:
        return []
    t = ''.join(c for c in text.lower() if c.isalpha())
    hits = set()
    for i in range(len(t)):
        for L in range(minlen, 9):
            if i + L <= len(t) and t[i:i + L] in WORDS:
                hits.add(t[i:i + L])
    return sorted(hits)


# ------------------------------------------------------------------ reports
def spectrograms(x, sr, outdir, stem):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return []
    S, f, t = stft(x, sr, 4096, 1024)
    db = 20 * np.log10(S + 1e-10)
    made = []
    views = [('full', 0, sr / 2), ('lo', 0, 4000),
             ('mid', 3000, 10000), ('hi', 10000, sr / 2)]
    for name, a, b in views:
        sel = (f >= a) & (f <= b)
        if sel.sum() < 4:
            continue
        d = db[sel]
        # per-view contrast stretch so a faint payload is still visible
        vmin = np.percentile(d, 55)
        vmax = np.percentile(d, 99.9)
        plt.figure(figsize=(22, 6), dpi=110)
        plt.imshow(d, origin='lower', aspect='auto', cmap='magma',
                   vmin=vmin, vmax=vmax,
                   extent=[t[0], t[-1], f[sel][0], f[sel][-1]])
        plt.xlabel('seconds'); plt.ylabel('Hz')
        plt.title(f'{stem} [{name}] {a:.0f}-{b:.0f} Hz')
        plt.colorbar(label='dB')
        p = os.path.join(outdir, f'{stem}_{name}.png')
        plt.tight_layout(); plt.savefig(p); plt.close()
        made.append(p)
    return made


def analyse(path, outdir):
    stem = os.path.splitext(os.path.basename(path))[0]
    x, sr, nch, sw, chans = read_wav(path)
    rep = {'file': os.path.basename(path), 'sr': sr, 'channels': nch,
           'seconds': round(len(x) / sr, 2), 'sampwidth_bytes': sw}
    print(f'\n=== {stem} === {rep["seconds"]}s {sr}Hz {nch}ch {sw*8}bit')

    S, f, _ = stft(x, sr, 4096, 2048)
    tot = S.sum() + 1e-9
    for lo, hi, lab in ((13000, sr / 2, '>13k'), (16000, sr / 2, '>16k'),
                        (19000, sr / 2, '>19k')):
        sel = (f >= lo) & (f <= hi)
        rep[f'energy_{lab}'] = float(S[sel].sum() / tot) if sel.any() else 0.0
    print(f'  high-band energy: >13k {rep["energy_>13k"]:.2e}  '
          f'>16k {rep["energy_>16k"]:.2e}  >19k {rep["energy_>19k"]:.2e}')

    if nch == 2:
        d = chans[:, 0] - chans[:, 1]
        rep['mid_side_ratio'] = float(np.abs(d).mean() /
                                      (np.abs(x).mean() + 1e-9))
        print(f'  side/mid amplitude ratio: {rep["mid_side_ratio"]:.4f}'
              '   (a large value can hide a payload in the side channel)')

    dm, nmarks = drum_morse(x, sr)
    rep['drum_morse'] = dm; rep['drum_onsets'] = nmarks
    if dm.strip('?  '):
        print(f'  drum-morse ({nmarks} onsets): {dm[:180]}')
        w = substr_words(dm)
        if w:
            print(f'    ** BIP39 substrings: {w}')
            rep['drum_morse_words'] = w

    for lo, hi in ((500, 1200), (1200, 2500), (2500, 5000)):
        tm = tone_morse(x, sr, lo, hi)
        if tm and tm.strip('?'):
            w = substr_words(tm)
            if w:
                print(f'  tone-morse {lo}-{hi}Hz: {tm[:120]}')
                print(f'    ** BIP39 substrings: {w}')
                rep.setdefault('tone_morse', {})[f'{lo}-{hi}'] = \
                    {'text': tm[:200], 'words': w}

    sc, st = sstv_score(x, sr)
    rep['sstv_score'] = sc; rep['sstv_time'] = st
    if sc > 0.45:
        print(f'  ** possible SSTV / tone payload: score {sc:.2f} at {st:.1f}s')

    dt = dtmf(x, sr)
    if dt:
        rep['dtmf'] = dt[:60]
        print(f'  ** DTMF digits: {"".join(k for _, k in dt[:60])}')

    ls = lsb_text(chans, sw)
    keep = [(o, r) for o, r in ls if find_words(r) or
            sum(c.isalpha() for c in r) > len(r) * 0.7]
    if keep:
        rep['lsb'] = keep[:12]
        print('  ** LSB printable runs:')
        for o, r in keep[:12]:
            print(f'     [{o}] {r}')

    made = spectrograms(x, sr, outdir, stem)
    rep['spectrograms'] = [os.path.basename(m) for m in made]
    if made:
        print(f'  spectrograms: {", ".join(os.path.basename(m) for m in made)}')
    return rep


# ----------------------------------------------------------------- selftest
def selftest():
    """synthesise a track carrying Morse on kick/snare and confirm recovery"""
    print('SELFTEST: building a synthetic track with drum-Morse "moon"')
    sr = 44100
    word = 'moon'
    code = {c: k for k, c in MORSE.items()}
    # index the letters, so repeated letters ("ss") still get a letter gap
    seq = [(li, s) for li, c in enumerate(word) for s in code[c]]
    unit = 0.12
    dur = len(seq) * unit * 3 + 2
    x = (np.random.randn(int(sr * dur)) * 0.002).astype(np.float32)
    t = 0.5
    prev = None
    for c, sym in seq:
        if prev is not None and prev != c:
            t += unit * 3           # letter gap
        n = int(sr * 0.05)
        idx = int(t * sr)
        env = np.exp(-np.linspace(0, 8, n)).astype(np.float32)
        if sym == '-':              # kick: low sine
            tone = np.sin(2 * np.pi * 65 * np.arange(n) / sr).astype(np.float32)
        else:                       # snare: band noise
            tone = np.random.randn(n).astype(np.float32)
            tone = np.convolve(tone, np.ones(3) / 3, 'same')
        x[idx:idx + n] += (tone * env * 0.7).astype(np.float32)
        t += unit
        prev = c
    got, n = drum_morse(x, sr)
    print(f'  onsets={n}  decoded={got!r}')
    hits = substr_words(got)
    print(f'  BIP39 substrings found: {hits}')
    ok = 'moon' in got.replace(' ', '') or 'moon' in hits
    print('  RESULT:', 'PASS - detector recovers drum-Morse' if ok
          else 'FAIL - decoder did not recover the planted word')
    # LSB round-trip
    msg = b'turtle vintage'
    base = (np.random.randn(len(msg) * 8) * 0.1)
    ints = np.round(base * 32768).astype(np.int64)
    bits = np.unpackbits(np.frombuffer(msg, np.uint8).reshape(-1, 1), axis=1).ravel()
    ints = (ints & ~1) | bits
    ch = (ints.astype(np.float32) / 32768.0).reshape(-1, 1)
    runs = lsb_text(ch, 2)
    found = any('turtle' in r for _, r in runs)
    print('  LSB round-trip:', 'PASS' if found else 'FAIL')
    return ok and found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', nargs='?', help='folder containing the WAVs')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.directory:
        ap.error('give the folder containing the 12 .wav files')
    files = sorted(f for f in os.listdir(a.directory)
                   if f.lower().endswith('.wav') and not f.startswith('._'))
    if not files:
        print('No .wav files found. Note: files starting with "._" are macOS '
              'resource-fork stubs, not audio - use the real ones.')
        sys.exit(1)
    outdir = os.path.join(a.directory, '_analysis')
    os.makedirs(outdir, exist_ok=True)
    print(f'{len(files)} tracks -> {outdir}')
    if not WORDS:
        print('NOTE: `pip install mnemonic` to enable BIP39 word matching.')
    reps = []
    for fn in files:
        try:
            reps.append(analyse(os.path.join(a.directory, fn), outdir))
        except Exception as e:
            print(f'  !! {fn}: {e}')
    with open(os.path.join(outdir, 'report.json'), 'w') as fh:
        json.dump(reps, fh, indent=1)
    print(f'\nWrote {outdir}/report.json plus spectrogram PNGs.')
    print('Send back report.json and the PNGs (the "lo" and "full" views '
          'matter most).')


if __name__ == '__main__':
    main()
