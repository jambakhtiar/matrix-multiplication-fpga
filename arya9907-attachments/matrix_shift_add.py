import numpy as np
from computationcoding.decomp_pwr2 import power2decomp as dp2d
from computationcoding.distortion import SNRmat as SNRmat
from computationcoding.no_add import no_add_MPA as get_adds
from computationcoding.csd_conv import to_csd
import csv

def get_shifts(value, total_bits=16, decimal_bits=8):
    """
    Computes the minimal set of shifts for a given fixed-point number and prints detailed shift info.

    :param value: The floating-point value to convert
    :param total_bits: Total bit width of the fixed-point representation
    :param decimal_bits: Number of fractional bits
    :return: List of shifts (position, sign, power of 2, shifts needed)
    """
    shifts = []
    csd = to_csd(value, total_bits - decimal_bits, total_bits)
    print(f"CSD Representation for {value}: {csd}")
    for i, bit in enumerate(csd):
        if bit != 0:
            shift_position = total_bits - decimal_bits - i - 1
            abs_position = abs(shift_position)
            power_of_2 = 2 ** abs_position
            shifts_needed = abs_position
            sign = bit > 0
            shifts.append((abs_position, sign, power_of_2, shifts_needed))
            print(f"Value: {value}, Abs Position: {abs_position}, Power of 2: {power_of_2}, Shifts Needed: {shifts_needed}, Sign: {'+' if sign else '-'}")
    return shifts

def p2d_decomp(M, S, E=2, sqnr_target=48, verbose=False):
    def slice_mat(M, S):
        return [M[:, sum(S[:i-1]):sum(S[:i])] for i in range(1, len(S)+1)]

    mats = slice_mat(M, S)
    # Print each slice and its entries
    for i, mat in enumerate(mats):
        print(f"Slice {i+1}:")
        print(mat)
        print()

    factors = [[np.eye(*mats[s].shape)] for s in range(len(S))]
    approxes = [np.eye(*mats[s].shape) for s in range(len(S))]
    snr = 0
    p = 0
    adds = 0
    combined_data = []

    while snr < sqnr_target:
        p += 1
        for s in range(len(S)):
            W = dp2d(mats[s].T, approxes[s].T, E).T
            approxes[s] = W @ approxes[s]
            factors[s].append(W)
            if verbose:
                print(p, s, SNRmat(mats[s], approxes[s]))
            adds += get_adds(W)
            # Collect shifts data
            slice_shifts_data = []
            for row_idx, row in enumerate(W):
                row_shifts = []
                for co_idx, val in enumerate(row):
                    if val != 0:
                        print(s, len(factors[s]), row_idx, co_idx)
                        shifts = get_shifts(val)
                        row_shifts.extend(shifts)
                        print()
                slice_shifts_data.append(row_shifts)
                combined_data.append((s+1, len(factors[s]), row_shifts))  # Add slice index, factor index, and shifts data
        snr = SNRmat(M, np.concatenate(approxes, axis=1))
        if verbose:
            print(p, snr, adds)
        if p > 200:
            return None

    # Print the decomposed matrix of each slice
    for i, mat in enumerate(approxes):
        print(f"Decomposed matrix of slice {i+1}:")
        print(mat)
        print()

    # Print each factor matrix
    for i, factor_list in enumerate(factors):
        print(f"Factor matrices of slice {i+1}:")
        for j, factor in enumerate(factor_list):
            print(f"Factor {j+1}:")
            print(factor)
            print()

    # Save combined data to CSV
    with open("combined_data.csv", "w", newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["slice_idx", "factor_idx", "shifts"])
        for row in combined_data:
            shifts_str = ";".join([f"({pos},{int(sign)},{pow2},{shifts})" for pos, sign, pow2, shifts in row[2]])
            if len(row[2]) < 1:
                print(f"Warning: No shift data for slice {row[0]} factor {row[1]}")
            csvwriter.writerow([row[0], row[1], shifts_str])

    return factors, snr, adds, p

if __name__ == "__main__":
    M = np.array([
        [-1.69329896,  9.93983555,  3.45591554,  0.40096005],
        [0.44056083,  8.05752756,  6.12243244, -2.07345733],
        [-2.63289454,  2.15537012, -3.91722353, -4.00861293],
        [-2.9187763,   7.07731591, -3.9351276,   2.9654481]
    ])  # 4x4 matrix
    S = [2, 2]  # number of slices
    factors, snr, adds, p = p2d_decomp(M, S)
    print(f"Factors: {p}")
    print(f"Additions: {adds}")
    print(f"SQNR: {snr:.2f} dB")
