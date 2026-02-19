"""
Benchmark: Sequential (pre-optimization) vs Parallel (optimized) simulation.

Compares wall-clock time for the same simulation scenario:
  - Test A: Sequential execution (for-loop, simulating pre-optimization code)
  - Test B: Parallel execution (ThreadPoolExecutor, current optimized code)

Usage:
  cd reverie/backend_server
  uv run python benchmark.py

Measures three phases:
  1. First day init (steps 0-10): hourly schedule batch generation effect
  2. Skip sleeping (2900 steps): fast-forward baseline
  3. Active period (30 steps): full cognitive cycle with parallelization
"""
import sys
import os
import time
import json
import shutil
import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")

from reverie import ReverieServer

# ---------- Configuration ----------
SIM_ORIGIN = "base_the_ville_isabella_maria_klaus"
SIM_SEQ = "bench_sequential"
SIM_PAR = "bench_parallel"

PHASE1_STEPS = 10    # First day initialization
PHASE2_STEPS = 2900  # Skip sleeping period
PHASE3_STEPS = 30    # Active morning period

# ---------- Headless loop implementations ----------

def run_headless_sequential(rs, n_steps):
    """
    Sequential headless loop -- simulates pre-optimization behavior.
    Phase A runs in a for-loop (no ThreadPoolExecutor).
    """
    game_obj_cleanup = dict()

    for step in range(n_steps):
        # Clean up object actions from previous cycle
        for key, val in game_obj_cleanup.items():
            rs.maze.turn_event_from_tile_idle(key, val)
        game_obj_cleanup = dict()

        # Update maze state for each persona
        for persona_name, persona in rs.personas.items():
            curr_tile = rs.personas_tile[persona_name]
            new_tile = curr_tile

            rs.maze.remove_subject_events_from_tile(persona.name, curr_tile)
            rs.maze.add_event_from_tile(
                persona.scratch.get_curr_event_and_desc(), new_tile)

            if not persona.scratch.planned_path:
                game_obj_cleanup[persona.scratch
                                 .get_curr_obj_event_and_desc()] = new_tile
                rs.maze.add_event_from_tile(
                    persona.scratch.get_curr_obj_event_and_desc(), new_tile)
                blank = (persona.scratch.get_curr_obj_event_and_desc()[0],
                         None, None, None)
                rs.maze.remove_event_from_tile(blank, new_tile)

        # Phase A: SEQUENTIAL (pre-optimization)
        phase_a_results = {}
        for persona_name, persona in rs.personas.items():
            curr_tile = rs.personas_tile[persona_name]
            phase_a_results[persona_name] = persona.move_phase_a(
                rs.maze, curr_tile, rs.curr_time)

        # Phase B: sequential (same as optimized version)
        for persona_name, persona in rs.personas.items():
            new_day, retrieved = phase_a_results[persona_name]
            next_tile, pronunciatio, description = persona.move_phase_b(
                rs.maze, rs.personas, retrieved)

            old_tile = rs.personas_tile[persona_name]
            rs.personas_tile[persona_name] = next_tile
            rs.maze.remove_subject_events_from_tile(persona.name, old_tile)
            rs.maze.add_event_from_tile(
                persona.scratch.get_curr_event_and_desc(), next_tile)

        # Advance time
        rs.step += 1
        rs.curr_time += datetime.timedelta(seconds=rs.sec_per_step)

        if (step + 1) % 100 == 0:
            print(f"    [SEQ] step {step + 1}/{n_steps} "
                  f"(time: {rs.curr_time.strftime('%H:%M:%S')})")


def run_headless_parallel(rs, n_steps):
    """
    Parallel headless loop -- current optimized implementation.
    Phase A runs in ThreadPoolExecutor (created once, reused across steps).
    """
    game_obj_cleanup = dict()

    with ThreadPoolExecutor(
            max_workers=min(len(rs.personas), 8)) as executor:
        for step in range(n_steps):
            # Clean up object actions from previous cycle
            for key, val in game_obj_cleanup.items():
                rs.maze.turn_event_from_tile_idle(key, val)
            game_obj_cleanup = dict()

            # Update maze state for each persona
            for persona_name, persona in rs.personas.items():
                curr_tile = rs.personas_tile[persona_name]
                new_tile = curr_tile

                rs.maze.remove_subject_events_from_tile(persona.name, curr_tile)
                rs.maze.add_event_from_tile(
                    persona.scratch.get_curr_event_and_desc(), new_tile)

                if not persona.scratch.planned_path:
                    game_obj_cleanup[persona.scratch
                                     .get_curr_obj_event_and_desc()] = new_tile
                    rs.maze.add_event_from_tile(
                        persona.scratch.get_curr_obj_event_and_desc(), new_tile)
                    blank = (persona.scratch.get_curr_obj_event_and_desc()[0],
                             None, None, None)
                    rs.maze.remove_event_from_tile(blank, new_tile)

            # Phase A: PARALLEL (optimized)
            phase_a_results = {}
            futures = {}
            for persona_name, persona in rs.personas.items():
                curr_tile = rs.personas_tile[persona_name]
                futures[persona_name] = executor.submit(
                    persona.move_phase_a,
                    rs.maze, curr_tile, rs.curr_time)
            for persona_name, future in futures.items():
                phase_a_results[persona_name] = future.result()

            # Phase B: sequential (same as sequential version)
            for persona_name, persona in rs.personas.items():
                new_day, retrieved = phase_a_results[persona_name]
                next_tile, pronunciatio, description = persona.move_phase_b(
                    rs.maze, rs.personas, retrieved)

                old_tile = rs.personas_tile[persona_name]
                rs.personas_tile[persona_name] = next_tile
                rs.maze.remove_subject_events_from_tile(persona.name, old_tile)
                rs.maze.add_event_from_tile(
                    persona.scratch.get_curr_event_and_desc(), next_tile)

            # Advance time
            rs.step += 1
            rs.curr_time += datetime.timedelta(seconds=rs.sec_per_step)

            if (step + 1) % 100 == 0:
                print(f"    [PAR] step {step + 1}/{n_steps} "
                      f"(time: {rs.curr_time.strftime('%H:%M:%S')})")


# ---------- Benchmark runner ----------

def run_benchmark(label, sim_name, run_fn, phases):
    """
    Run a complete benchmark for one mode (sequential or parallel).

    Args:
        label: Display label (e.g., "SEQUENTIAL", "PARALLEL")
        sim_name: Simulation fork name
        run_fn: The headless loop function to use
        phases: List of (phase_name, n_steps) tuples
    Returns:
        dict mapping phase_name -> elapsed_seconds
    """
    print(f"\n{'='*60}")
    print(f"  {label} BENCHMARK")
    print(f"{'='*60}")

    # Initialize server (fork from base)
    print(f"  Initializing ReverieServer (fork: {SIM_ORIGIN} -> {sim_name})...")
    t0 = time.time()
    rs = ReverieServer(SIM_ORIGIN, sim_name)
    init_time = time.time() - t0
    print(f"  Init: {init_time:.2f}s")
    print(f"  Personas: {list(rs.personas.keys())}")
    print(f"  Start time: {rs.curr_time.strftime('%B %d, %Y, %H:%M:%S')}")
    print()

    results = {}
    for phase_name, n_steps in phases:
        print(f"  --- Phase: {phase_name} ({n_steps} steps) ---")
        t_start = time.time()
        run_fn(rs, n_steps)
        elapsed = time.time() - t_start
        results[phase_name] = elapsed
        print(f"  -> {phase_name}: {elapsed:.2f}s "
              f"({elapsed/n_steps:.4f}s/step) "
              f"[game time: {rs.curr_time.strftime('%H:%M:%S')}]")
        print()

    # Save and return
    rs.save()
    results["total"] = sum(results.values())
    return results


def cleanup_sim(sim_name):
    """Remove simulation directory if it exists."""
    from utils import fs_storage
    sim_folder = f"{fs_storage}/{sim_name}"
    if os.path.exists(sim_folder):
        shutil.rmtree(sim_folder)


def print_comparison(seq_results, par_results, phases):
    """Print a formatted comparison table."""
    print()
    print("=" * 70)
    print("  BENCHMARK RESULTS: Sequential vs Parallel")
    print("=" * 70)
    print()
    print(f"  {'Phase':<25} {'Sequential':>10} {'Parallel':>10} {'Speedup':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

    for phase_name, _ in phases:
        seq_t = seq_results[phase_name]
        par_t = par_results[phase_name]
        speedup = seq_t / par_t if par_t > 0 else float('inf')
        print(f"  {phase_name:<25} {seq_t:>9.2f}s {par_t:>9.2f}s {speedup:>9.2f}x")

    seq_total = seq_results["total"]
    par_total = par_results["total"]
    total_speedup = seq_total / par_total if par_total > 0 else float('inf')
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
    print(f"  {'TOTAL':<25} {seq_total:>9.2f}s {par_total:>9.2f}s "
          f"{total_speedup:>9.2f}x")
    print()
    print(f"  Overall speedup: {total_speedup:.2f}x faster with parallelization")
    print()


# ---------- Main ----------

if __name__ == "__main__":
    phases = [
        ("first_day_init", PHASE1_STEPS),
        ("sleeping_skip", PHASE2_STEPS),
        ("active_period", PHASE3_STEPS),
    ]

    # Clean up any previous benchmark runs
    print("Cleaning up previous benchmark data...")
    cleanup_sim(SIM_SEQ)
    cleanup_sim(SIM_PAR)

    # Run sequential benchmark
    seq_results = run_benchmark(
        "SEQUENTIAL (pre-optimization)",
        SIM_SEQ,
        run_headless_sequential,
        phases,
    )

    # Clean up sequential sim to free disk space
    cleanup_sim(SIM_SEQ)

    # Run parallel benchmark
    par_results = run_benchmark(
        "PARALLEL (optimized)",
        SIM_PAR,
        run_headless_parallel,
        phases,
    )

    # Clean up parallel sim
    cleanup_sim(SIM_PAR)

    # Print comparison
    print_comparison(seq_results, par_results, phases)
