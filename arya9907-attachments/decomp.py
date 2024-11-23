import numpy as np

from computationcoding.decomp_pwr2 import power2decomp as dp2d
from computationcoding.lzdecomp import fastlzdecomp as dlzd

from computationcoding.distortion import SNRmat as SNRmat
from computationcoding.no_add import no_add_MPA as get_adds


def slice_mat(M, S):
    """Slice a matrix and return its slices as a list of np.array

    :M: input matrix
    :S: list of slice widths (number of columns)
    :returns: list of matrix slices

    """
    mats = [M[:, sum(S[:i-1]):sum(S[:i])] for i in range(1, len(S)+1)]
    return mats


def decomp_p2d(D, M, mats, E, S, sqnr_target=48, verbose=False):
    """Decompose a matrix using the DMP computation coding decomposition (P2D)

    :D: shape of the original matrix (tuple of (rows,cols))
    :M: original matrix (np.array)
    :mats: matrix slices
    :E: number of entries per row in the decomposition (2 or 3)
    :S: list of slice widths (number of columns per slice)
    :sqnr_target: target accuracy in dB; default: 48
    :verbose: print information on the decomposition (default False)
    :returns: list of decompositions (one entry for each slice), final accuracy in dB, total number of additions, number of factors

    """
    factors = [[np.eye(*mats[s].shape)] for s in range(len(S))]
    approxes = [np.eye(*mats[s].shape) for s in range(len(S))]
    snr = 0
    p = 0
    adds = 0
    while snr < sqnr_target:
        p += 1
        for s in range(len(S)):
            W = dp2d(mats[s].T, approxes[s].T, E).T
            approxes[s] = W @ approxes[s]
            factors[s].append(W)
            if verbose:
                print(p, s, SNRmat(mats[s], approxes[s]))
            adds += get_adds(W)
        snr = SNRmat(M, np.concatenate(approxes, axis=1))
        if verbose:
            print(p, snr, adds)
        if p > 200:
            return None
    return factors, snr, adds, p


def decomp_lzd(D, M, sqnr_target=48, max_add=20, verbose=False):
    """Decompose a matrix using the lempelzip-inspired computation coding decomposition (LZD)

    :D: shape of the original matrix (tuple of (rows,cols))
    :M: original matrix (np.array)
    :sqnr_target: target accuracy in dB; default: 48
    :verbose: print information on the decomposition (default False)
    :returns: list of decompositions (one entry for each slice), final accuracy in dB, total number of additions, number of factors

    """
    P, W, Pj, adds = dlzd(M, sqnr_target, max_add=max_add)
    if verbose:
        print(M)
        print(P)
    return W+[Pj], SNRmat(M, P), adds, len(W)+1


def generate_all_slicings(tot, y):
    """Generates all possible slicings for given dimensions

    :tot: Total number of columns of the matrix
    :y: Maximum single slice width
    :returns: List of slice widths

    """
    slicings_done = []
    factors = list(range(1,y+1))
    ss = [[x] for x in factors]
    while len(ss) > 0:
        s, ss = ss[0], ss[1:]
        for f in factors:
            if sum(s) + f > tot:
                continue
            x = s + [f]
            if sum(x) == tot:
                slicings_done.append(x)
            else:
                ss.append(x)
    return slicings_done


def test(y=4, E=2, mode="p2d lzd", lzd_maxadd=np.infty):
    """Test function for the decomposition.
    Generates a square matrix of given dimension.
    Decomposes with p2d with several slicings and LZD.
    Prints output to STDOUT.

    :y: Dimension of the matrix
    :E: number of operands per row for P2D
    :mode: string, can contain "p2d" or "lzd"
    :lzd_maxadd: number of maximum additions for LZD
    :returns: None

    """
    D = (y,y)
    M = np.random.rand(*D)*2-1
    print("Target matrix:")
    print(M)
    print()
    slicings = [[1]*4, [2,2], [4]]
    E = 2
    for S in slicings:
        mats = slice_mat(M, S)
        if "p2d" in mode:
            r = decomp_p2d(D, M, mats, E, S)
            if r:
                dec, snr, adds, p = r
                print("P2D")
                print(f"Slicing: {S}")
                print(f"SQNR: {snr:.2f} dB")
                print(f"Additions: {adds}")
                print(f"Factors: {p}")
            else:
                print("P2D")
                print(f"Slicing: {S}")
                print("Failed, too many factors.")
            print()
    if "lzd" in mode:
        dec, snr, adds, p = decomp_lzd(D, M, max_add=lzd_maxadd)
        print("LZD")
        print(f"SQNR: {snr:.2f} dB")
        print(f"Additions: {adds}")
        print(f"Factors: {p}")
        print()


if __name__ == "__main__":
    test()
