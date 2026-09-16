"""Explicit 1D diffusion solver and verification cases.

Implements the specification in SOLVER (2).pdf:
    c_t = D c_xx
with Forward Euler in time, central differences in space, and reflected
ghost nodes for homogeneous Neumann boundaries.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Problem:
    length: float = 1.0
    diffusivity: float = 2.0
    pulse_left: float = 0.4
    pulse_right: float = 0.6
    pulse_concentration: float = 1.0
    final_time: float = 0.020


def grid_and_initial_condition(problem: Problem, n: int) -> tuple[np.ndarray, np.ndarray, float]:
    dx = problem.length / n
    x = np.arange(n + 1, dtype=float) * dx
    c = np.zeros(n + 1, dtype=float)
    inside = (x > problem.pulse_left) & (x < problem.pulse_right)
    edges = np.isclose(x, problem.pulse_left) | np.isclose(x, problem.pulse_right)
    c[inside] = problem.pulse_concentration
    c[edges] = 0.5 * problem.pulse_concentration
    return x, c, dx


def reference_solution(x: np.ndarray, time: float, problem: Problem, terms: int = 1000) -> np.ndarray:
    result = np.full_like(x, problem.pulse_concentration *
                          (problem.pulse_right - problem.pulse_left) / problem.length)
    if time == 0.0:
        return result
    m = np.arange(1, terms + 1, dtype=float)[:, None]
    coefficients = (2.0 * problem.pulse_concentration / (math.pi * m)
                    * (np.sin(m * math.pi * problem.pulse_right / problem.length)
                       - np.sin(m * math.pi * problem.pulse_left / problem.length)))
    modes = np.cos(m * math.pi * x[None, :] / problem.length)
    decay = np.exp(-problem.diffusivity * (m * math.pi / problem.length) ** 2 * time)
    return result + np.sum(coefficients * modes * decay, axis=0)


def trapezoidal_mass(c: np.ndarray, dx: float) -> float:
    return dx * (0.5 * c[0] + np.sum(c[1:-1]) + 0.5 * c[-1])


def solve(problem: Problem, n: int, dt: float, output_times: tuple[float, ...] = ()) -> dict[float, np.ndarray]:
    x, c, dx = grid_and_initial_condition(problem, n)
    r = problem.diffusivity * dt / dx**2
    if not 0.0 <= r <= 0.5:
        raise ValueError(f"unstable diffusion number r={r}; require 0 <= r <= 0.5")
    requested = sorted(set(output_times) | {0.0})
    results = {0.0: c.copy()}
    current_time = 0.0
    for target in requested[1:]:
        while current_time < target - 1e-14:
            step = min(dt, target - current_time)
            if not math.isclose(step, dt):
                raise ValueError("output times must be integer multiples of dt")
            old = c.copy()
            # Interior: c_i^(n+1) = c_i^n + r(c_(i+1)^n - 2c_i^n + c_(i-1)^n)
            c[1:-1] = old[1:-1] + r * (old[2:] - 2.0 * old[1:-1] + old[:-2])
            # Reflected ghost nodes: c_-1=c_1 and c_(N+1)=c_(N-1).
            c[0] = old[0] + 2.0 * r * (old[1] - old[0])
            c[-1] = old[-1] + 2.0 * r * (old[-2] - old[-1])
            current_time += dt
        results[target] = c.copy()
    return results


def l2_error(error: np.ndarray, dx: float, length: float) -> float:
    return math.sqrt(dx / length * (0.5 * error[0]**2 + np.sum(error[1:-1]**2) + 0.5 * error[-1]**2))


def rms_difference(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def write_solution_csv(path: Path, x: np.ndarray, time: float, numerical: np.ndarray, reference: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time s", "x m", "c numerical mol m3", "c reference mol m3", "error signed mol m3", "abs error mol m3"])
        for xi, cn, cr in zip(x, numerical, reference):
            writer.writerow([time, xi, cn, cr, cn - cr, abs(cn - cr)])


def run_all_cases(output_root: str | Path = "results") -> None:
    problem = Problem()
    root = Path(output_root)
    common_times = (0.0, 0.002, 0.004, 0.010, 0.020)
    refinement = [(10, 0.002), (20, 0.0005), (40, 0.000125), (80, 0.00003125), (160, 0.0000078125), (320, 0.000001953125)]
    for n, dt in refinement:
        x, _, dx = grid_and_initial_condition(problem, n)
        solutions = solve(problem, n, dt, common_times)
        for time, numerical in solutions.items():
            reference = reference_solution(x, time, problem)
            write_solution_csv(root / "solutions" / f"N{n:03d}_t{time:.6f}.csv", x, time, numerical, reference)

    # Reference-series truncation check required by the specification.
    x, _, _ = grid_and_initial_condition(problem, 320)
    for time in common_times[1:]:
        difference = np.max(np.abs(reference_solution(x, time, problem, 2000) - reference_solution(x, time, problem, 1000)))
        print(f"reference truncation t={time:g}: {difference:.6e}")

    make_plots(problem, root, refinement, common_times)


def make_plots(problem: Problem, root: Path, refinement: list[tuple[int, float]], times: tuple[float, ...]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots()
    # Keep the profile figure readable; all cases remain available in CSV files.
    plot_meshes = {10, 160, 320}
    for n, dt in refinement:
        if n not in plot_meshes:
            continue
        x, _, _ = grid_and_initial_condition(problem, n)
        solutions = solve(problem, n, dt, times)
        for time in times:
            ax.plot(x, solutions[time], label=f"N={n}, t={time:g}")
    ax.set(xlabel="x (m)", ylabel="c (mol m$^{-3}$)", title="Numerical concentration profiles")
    ax.legend(fontsize=7, ncol=2)
    fig.savefig(root / "numerical_profiles.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    n, dt = refinement[-1]
    x, _, _ = grid_and_initial_condition(problem, n)
    numerical = solve(problem, n, dt, (problem.final_time,))[problem.final_time]
    reference = reference_solution(x, problem.final_time, problem)
    fig, ax = plt.subplots()
    ax.plot(x, numerical, label="numerical")
    ax.plot(x, reference, "--", label="reference")
    ax.set(xlabel="x (m)", ylabel="c (mol m$^{-3}$)", title="Final-time comparison")
    ax.legend()
    fig.savefig(root / "final_comparison.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    run_all_cases()
